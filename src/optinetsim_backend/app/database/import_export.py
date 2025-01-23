from flask_restful import Resource
from flask import Response, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from src.optinetsim_backend.app.config import Config
from src.optinetsim_backend.app.database.models import NetworkDB, db
from collections import OrderedDict
import json

client = MongoClient(Config.MONGO_URI)

def convert_objectid_and_datetime(data):
    if isinstance(data, list):
        return [convert_objectid_and_datetime(item) for item in data]
    elif isinstance(data, dict):
        return {
            key: convert_objectid_and_datetime(value)
            for key, value in data.items()
        }
    elif isinstance(data, ObjectId):
        return str(data)  # 将 ObjectId 转换为字符串
    elif isinstance(data, datetime):
        return data.isoformat()  # 将 datetime 转换为 ISO 格式
    else:
        return data


class NetworkExportResource(Resource):
    @jwt_required()
    def get(self, network_id):
        try:
            user_id = get_jwt_identity()

            # 查询网络信息
            network = NetworkDB.find_by_network_id(user_id, network_id)
            if not network:
                return {"message": "Network not found or access denied."}, 404

            # 转换 ObjectId 和 datetime
            network = convert_objectid_and_datetime(network)

            # 删除 user_id 字段
            network.pop("user_id", None)

            # 获取设备库 ID 数组
            equipment_library_ids = network.get("equipment_library_ids", [])
            if not equipment_library_ids:
                return {"message": "No equipment libraries are associated with this network."}, 404

            # 查询所有关联的设备库
            equipment_libraries = list(
                db.equipment_libraries.find({"_id": {"$in": [ObjectId(lid) for lid in equipment_library_ids]}})
            )
            if not equipment_libraries:
                return {"message": "No equipment libraries found."}, 404

            # 转换设备库数据中的 ObjectId 和 datetime
            equipment_libraries = [convert_objectid_and_datetime(library) for library in equipment_libraries]

            # 删除设备库中的 user_id 字段
            for library in equipment_libraries:
                library.pop("user_id", None)

            # 构建响应
            response = OrderedDict({
                "network_name": network["network_name"],
                "elements": network.get("elements", []),
                "connections": network.get("connections", []),
                "services": network.get("services", []),
                "simulation_config": network.get("simulation_config", {}),
                "SI": network.get("SI", {}),
                "Span": network.get("Span", {}),
                "equipment_libraries": equipment_libraries
            })

            return Response(
                response=json.dumps(response),
                status=200,
                mimetype='application/json'
            )

        except Exception as e:
            return {"message": str(e)}, 500



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
            equipment_libraries = data.get("equipment_libraries", [])

            if not network_name:
                return {"message": "Network name is required"}, 400

            # 保存设备库并记录设备库 ID
            imported_library_ids = []
            for library in equipment_libraries:
                library['_id'] = ObjectId()  # 为设备库生成新的 ObjectId
                library['user_id'] = ObjectId(user_id)
                library['created_at'] = datetime.utcnow()
                library['updated_at'] = datetime.utcnow()
                db.equipment_libraries.insert_one(library)

                # 删除响应中不需要的字段
                library.pop('user_id', None)  # 移除 user_id
                imported_library_ids.append(str(library['_id']))

            # 构建网络数据
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
                "equipment_library_ids": imported_library_ids  # 设备库 ID 数组
            }

            result = db.networks.insert_one(network)

            # 构建响应数据
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
                "equipment_libraries": equipment_libraries
            })

            # 使用 convert_objectid_and_datetime 函数转换响应数据
            response = convert_objectid_and_datetime(response)

            # 返回响应数据
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
            merged[key] = merge_dicts(merged[key], value)  # 递序合并子字典
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


# 递序转换数据类型
def convert_objectid_and_datetime(data):
    if isinstance(data, list):
        return [convert_objectid_and_datetime(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_objectid_and_datetime(value) for key, value in data.items()}
    elif isinstance(data, ObjectId):  # 转换 ObjectId 为字符串
        return str(data)
    elif isinstance(data, datetime):  # 转换 datetime 为 ISO 格式字符串
        return data.isoformat()
    else:
        return data


class TopologyImportResource(Resource):
    @jwt_required()
    def post(self, network_id):
        try:
            user_id = get_jwt_identity()

            # 查询目标网络是否存在并属于当前用户
            network = db.networks.find_one({"_id": ObjectId(network_id), "user_id": ObjectId(user_id)})
            if not network:
                return {"message": "Network not found or access denied."}, 404

            # 获取请求数据
            data = request.get_json()
            if not data:
                return {"message": "Invalid request body"}, 400

            # 提取拟化相关数据
            elements = data.get("elements", [])
            connections = data.get("connections", [])
            services = data.get("services", [])
            simulation_config = data.get("simulation_config", {})
            SI = data.get("SI", {})
            Span = data.get("Span", {})
            equipment_libraries = data.get("equipment_libraries", [])

            # 处理设备库，确保不重复添加
            imported_library_ids = []
            for library in equipment_libraries:
                # 检查是否存在重复的设备库
                existing_library = db.equipment_libraries.find_one({
                    "library_name": library["library_name"],
                    "user_id": ObjectId(user_id)
                })

                if existing_library:
                    # 如果设备库已存在，只添加其 ID
                    imported_library_ids.append(str(existing_library["_id"]))
                else:
                    # 如果设备库不存在，创建新设备库
                    library["_id"] = ObjectId()
                    library["user_id"] = ObjectId(user_id)
                    library["created_at"] = datetime.utcnow()
                    library["updated_at"] = datetime.utcnow()
                    db.equipment_libraries.insert_one(library)
                    imported_library_ids.append(str(library["_id"]))

            # 保留原有的设备库列表，并合并新增的 ID
            existing_library_ids = network.get("equipment_library_ids", [])
            all_library_ids = list(set(existing_library_ids + imported_library_ids))

            # 更新拟化数据
            updated_elements = remove_duplicates(network.get("elements", []) + elements)
            updated_connections = remove_duplicates(network.get("connections", []) + connections)
            updated_services = remove_duplicates(network.get("services", []) + services)

            updated_SI = merge_dicts(network.get("SI", {}), SI)
            updated_Span = merge_dicts(network.get("Span", {}), Span)

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
                        "equipment_library_ids": all_library_ids,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            # 构建响应数据
            equipment_libraries_data = []
            for lib in db.equipment_libraries.find({"_id": {"$in": [ObjectId(lid) for lid in all_library_ids]}}):
                lib = convert_objectid_and_datetime(lib)  # 转换 ObjectId 和 datetime
                lib.pop("user_id", None)  # 删除 user_id 字段
                equipment_libraries_data.append(lib)

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
                "equipment_libraries": equipment_libraries_data
            })

            return Response(
                response=json.dumps(response),
                status=200,
                mimetype='application/json'
            )

        except Exception as e:
            return {"message": str(e)}, 500
