from flask_restful import Resource
from flask import Response, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from src.optinetsim_backend.app.config import Config
from src.optinetsim_backend.app.database.models import NetworkDB
from collections import OrderedDict
import json

client = MongoClient(Config.MONGO_URI)
db = client.optinetsim


class NetworkExportResource(Resource):
    @jwt_required()
    def get(self, network_id):
        try:

            user_id = get_jwt_identity()


            network = NetworkDB.find_by_network_id(user_id, network_id)
            if not network:
                return {"message": "Network not found or access denied."}, 404


            network["_id"] = str(network["_id"])
            network["user_id"] = str(network["user_id"])


            equipment_library_id = network.get("equipment_library_id")
            if not equipment_library_id:
                return {"message": "No equipment library is associated with this network."}, 404

            equipment_library = db.equipment_libraries.find_one({"_id": ObjectId(equipment_library_id)})
            if not equipment_library:
                return {"message": "Equipment library not found."}, 404


            equipment_library["_id"] = str(equipment_library["_id"])
            equipment_library["user_id"] = str(equipment_library["user_id"])
            equipment_library["created_at"] = equipment_library["created_at"].isoformat() if "created_at" in equipment_library else None
            equipment_library["updated_at"] = equipment_library["updated_at"].isoformat() if "updated_at" in equipment_library else None


            response = OrderedDict({
                "network_name": network["network_name"],
                "elements": network.get("elements", []),
                "connections": network.get("connections", []),
                "services": network.get("services", []),
                "simulation_config": network.get("simulation_config", {}),
                "SI": network.get("SI", {}),
                "Span": network.get("Span", {}),
                "equipment_library": equipment_library
            })


            return Response(
                response=json.dumps(response),
                status=200,
                mimetype='application/json'
            )

        except Exception as e:
            return {"message": str(e)}, 500



def convert_objectid_and_datetime(data):
    if isinstance(data, list):
        return [convert_objectid_and_datetime(item) for item in data]
    elif isinstance(data, dict):
        return {
            key: convert_objectid_and_datetime(value)
            for key, value in data.items()
        }
    elif isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data


class NetworkImportResource(Resource):
    @jwt_required()
    def post(self):
        try:

            user_id = get_jwt_identity()


            data = request.get_json()
            if not data:
                return {"message": "Invalid request body"}, 400


            network_name = data.get("network_name")
            elements = data.get("elements", [])
            connections = data.get("connections", [])
            services = data.get("services", [])
            simulation_config = data.get("simulation_config", {})
            SI = data.get("SI", {})
            Span = data.get("Span", {})
            equipment_library = data.get("equipment_library")  # 修改为单个设备库

            if not network_name:
                return {"message": "Network name is required"}, 400

            if not equipment_library:
                return {"message": "Equipment library is required"}, 400


            equipment_library['_id'] = ObjectId()  # 为设备库生成新的 ObjectId
            equipment_library['user_id'] = ObjectId(user_id)
            equipment_library['created_at'] = datetime.utcnow()
            equipment_library['updated_at'] = datetime.utcnow()
            db.equipment_libraries.insert_one(equipment_library)


            equipment_library['_id'] = str(equipment_library['_id'])
            equipment_library['user_id'] = str(equipment_library['user_id'])
            equipment_library['created_at'] = equipment_library['created_at'].isoformat()
            equipment_library['updated_at'] = equipment_library['updated_at'].isoformat()


            network = {
                "user_id": ObjectId(user_id),
                "network_name": network_name,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "elements": elements,
                "connections": connections,
                "services": services,
                "simulation_config": simulation_config,
                "SI": SI,
                "Span": Span,
                "equipment_library_id": ObjectId(equipment_library['_id'])  # 绑定设备库 ID
            }


            result = db.networks.insert_one(network)


            response = OrderedDict({
                "network_id": str(result.inserted_id),
                "network_name": network_name,
                "created_at": network["created_at"].strftime("%Y-%m-%d %H:%M"),
                "updated_at": network["updated_at"].strftime("%Y-%m-%d %H:%M"),
                "elements": elements,
                "connections": connections,
                "services": services,
                "simulation_config": simulation_config,
                "SI": SI,
                "Span": Span,
                "equipment_library": equipment_library
            })

            # 使用 json.dumps 保持顺序并返回
            return Response(
                response=json.dumps(response),
                status=200,
                mimetype='application/json'
            )

        except Exception as e:
            return {"message": str(e)}, 500



# 嵌套字典合并函数
def merge_dicts(old_dict, new_dict):
    merged = old_dict.copy()
    for key, value in new_dict.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_dicts(merged[key], value)  # 递归合并子字典
        else:
            merged[key] = value  # 使用新值覆盖旧值
    return merged


# 嵌套去重函数
def remove_duplicates(nested_list):
    if not nested_list:
        return []

    seen = set()
    result = []

    for item in nested_list:
        if isinstance(item, dict):
            marker = json.dumps(item, sort_keys=True)
        else:
            marker = item

        if marker not in seen:
            seen.add(marker)
            result.append(item)

    return result


# 递归转换数据类型
def convert_to_serializable(data):
    """
    将 ObjectId 和 datetime 转换为 JSON 可序列化的格式。
    """
    if isinstance(data, list):
        return [convert_to_serializable(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_to_serializable(value) for key, value in data.items()}
    elif isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, datetime):
        return data.isoformat()  # 转换为 ISO 格式
    else:
        return data


class TopologyImportResource(Resource):
    @jwt_required()
    def post(self, network_id):
        try:
            # 获取当前用户 ID
            user_id = get_jwt_identity()

            # 查询目标网络是否存在并属于当前用户
            network = db.networks.find_one({"_id": ObjectId(network_id), "user_id": ObjectId(user_id)})
            if not network:
                return {"message": "Network not found or access denied."}, 404

            # 获取请求数据
            data = request.get_json()
            if not data:
                return {"message": "Invalid request body"}, 400

            # 提取拓扑相关数据
            elements = data.get("elements", [])
            connections = data.get("connections", [])
            services = data.get("services", [])
            simulation_config = data.get("simulation_config", {})
            SI = data.get("SI", {})
            Span = data.get("Span", {})
            equipment_library = data.get("equipment_library")  # 修改为单个设备库

            if not equipment_library:
                return {"message": "Equipment library is required."}, 400

            # 查询网络绑定的设备库
            equipment_library_id = network.get("equipment_library_id")

            # 检查设备库是否已绑定
            if not equipment_library_id:
                # 如果设备库未绑定，则创建新的设备库并绑定
                equipment_library['_id'] = ObjectId()
                equipment_library['user_id'] = ObjectId(user_id)
                equipment_library['created_at'] = datetime.utcnow()
                equipment_library['updated_at'] = datetime.utcnow()
                db.equipment_libraries.insert_one(equipment_library)

                # 更新网络绑定的设备库 ID
                equipment_library_id = equipment_library['_id']
                db.networks.update_one(
                    {"_id": ObjectId(network_id)},
                    {"$set": {"equipment_library_id": equipment_library_id}}
                )
            else:
                # 如果设备库已绑定，则更新设备库
                existing_library = db.equipment_libraries.find_one({"_id": ObjectId(equipment_library_id)})
                if not existing_library:
                    return {"message": "Bound equipment library not found."}, 404

                for category, new_equipments in equipment_library.get("equipments", {}).items():
                    existing_equipments = existing_library["equipments"].get(category, [])
                    combined_equipments = list(set(existing_equipments + new_equipments))
                    existing_library["equipments"][category] = combined_equipments

                db.equipment_libraries.update_one(
                    {"_id": ObjectId(equipment_library_id)},
                    {
                        "$set": {
                            "equipments": existing_library["equipments"],
                            "updated_at": datetime.utcnow()
                        }
                    }
                )

            # 更新拓扑数据
            updated_elements = remove_duplicates(network.get("elements", []) + elements)
            updated_connections = remove_duplicates(network.get("connections", []) + connections)
            updated_services = remove_duplicates(network.get("services", []) + services)

            updated_SI = merge_dicts(network.get("SI", {}), SI)
            updated_Span = merge_dicts(network.get("Span", {}), Span)

            # 更新网络数据
            db.networks.update_one(
                {"_id": ObjectId(network_id)},
                {
                    "$set": {
                        "elements": updated_elements,
                        "connections": updated_connections,
                        "services": updated_services,
                        "simulation_config": simulation_config,
                        "SI": updated_SI,
                        "Span": updated_Span,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            # 构建响应数据
            equipment_library_response = db.equipment_libraries.find_one({"_id": ObjectId(equipment_library_id)})
            equipment_library_response["_id"] = str(equipment_library_response["_id"])
            equipment_library_response["user_id"] = str(equipment_library_response["user_id"])
            equipment_library_response["created_at"] = equipment_library_response["created_at"].isoformat()
            equipment_library_response["updated_at"] = equipment_library_response["updated_at"].isoformat()

            response = OrderedDict({
                "network_id": str(network["_id"]),
                "network_name": network["network_name"],
                "created_at": network["created_at"].strftime("%Y-%m-%d %H:%M"),
                "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "elements": updated_elements,
                "connections": updated_connections,
                "services": updated_services,
                "simulation_config": simulation_config,
                "SI": updated_SI,
                "Span": updated_Span,
                "equipment_library": convert_to_serializable(equipment_library_response)
            })

            # 返回响应数据
            return Response(
                response=json.dumps(response),
                status=200,
                mimetype='application/json'
            )

        except Exception as e:
            return {"message": str(e)}, 500


