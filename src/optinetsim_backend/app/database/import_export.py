import uuid
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

# 将 ObjectId 和 datetime 递归转换为字符串
def convert_objectid_and_datetime(data):
    if isinstance(data, list):
        return [convert_objectid_and_datetime(item) for item in data]
    elif isinstance(data, dict):
        return {key: convert_objectid_and_datetime(value) for key, value in data.items()}
    elif isinstance(data, ObjectId):
        return str(data)
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data

# 确保每个元素都有 element_id（如果没有则生成）
def ensure_element_id(elements):
    for element in elements:
        if "element_id" not in element:
            element["element_id"] = str(uuid.uuid4())
    return elements

# 合并设备库中的参数到元素中（依据 element 中的 library_id、type 与 type_variety）
def merge_library_params(elements, equipment_libraries):
    for element in elements:
        library_id = element.get("library_id")
        if library_id:
            library = next((lib for lib in equipment_libraries if str(lib["_id"]) == str(library_id)), None)
            if library:
                equipment = next(
                    (eq for eq in library["equipments"].get(element["type"], []) if eq["type_variety"] == element["type_variety"]),
                    None
                )
                if equipment:
                    element["params"] = {**equipment["params"], **element.get("params", {})}
    return elements

# 递归合并两个字典
def merge_dicts(old_dict, new_dict):
    merged = old_dict.copy()
    for key, value in new_dict.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged

# 去重，用于合并数组时防止重复数据
def remove_duplicates(nested_list):
    if not nested_list:
        return []
    seen = set()
    result = []
    for item in nested_list:
        marker = json.dumps(item, sort_keys=True)
        if marker not in seen:
            seen.add(marker)
            result.append(item)
    return result

######################################
# NetworkExportResource (导出网络数据)
######################################
class NetworkExportResource(Resource):
    @jwt_required()
    def get(self, network_id):
        try:
            user_id = get_jwt_identity()
            network = NetworkDB.find_by_network_id(user_id, network_id)
            if not network:
                return {"message": "Network not found or access denied."}, 404

            network = convert_objectid_and_datetime(network)
            network.pop("user_id", None)

            equipment_library_ids = network.get("equipment_library_ids", [])
            if not equipment_library_ids:
                return {"message": "No equipment libraries are associated with this network."}, 404

            equipment_libraries = list(
                db.equipment_libraries.find({"_id": {"$in": [ObjectId(lid) for lid in equipment_library_ids]}})
            )
            if not equipment_libraries:
                return {"message": "No equipment libraries found."}, 404

            equipment_libraries = [convert_objectid_and_datetime(lib) for lib in equipment_libraries]
            for lib in equipment_libraries:
                lib.pop("user_id", None)

            network["elements"] = ensure_element_id(network.get("elements", []))

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

######################################
# NetworkImportResource (新建网络数据)
######################################
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

            elements = ensure_element_id(elements)

            imported_library_ids = []
            for library in equipment_libraries:
                library['_id'] = ObjectId()
                library['user_id'] = ObjectId(user_id)
                library['created_at'] = datetime.utcnow()
                library['updated_at'] = datetime.utcnow()
                db.equipment_libraries.insert_one(library)
                library.pop('user_id', None)
                imported_library_ids.append(str(library['_id']))

            elements = merge_library_params(elements, equipment_libraries)

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
                "equipment_library_ids": imported_library_ids
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
                "equipment_libraries": equipment_libraries
            })

            response = convert_objectid_and_datetime(response)

            return Response(
                response=json.dumps(response),
                status=200,
                mimetype='application/json'
            )
        except Exception as e:
            return {"message": str(e)}, 500

######################################
# TopologyImportResource (拓扑追加更新)
######################################
class TopologyImportResource(Resource):
    @jwt_required()
    def post(self, network_id):
        try:
            user_id = get_jwt_identity()
            network = db.networks.find_one({"_id": ObjectId(network_id), "user_id": ObjectId(user_id)})
            if not network:
                return {"message": "Network not found or access denied."}, 404

            data = request.get_json()
            if not data:
                return {"message": "Invalid request body"}, 400

            elements = data.get("elements", [])
            connections = data.get("connections", [])
            services = data.get("services", [])
            simulation_config = data.get("simulation_config", {})
            SI = data.get("SI", {})
            Span = data.get("Span", {})
            equipment_libraries = data.get("equipment_libraries", [])

            # 处理设备库：对请求中每个设备库，如果没有 _id，则生成后插入数据库
            new_library_ids = []
            processed_equipment_libraries = []
            for library in equipment_libraries:
                if "_id" not in library:
                    library['_id'] = ObjectId()
                    library['user_id'] = ObjectId(user_id)
                    library['created_at'] = datetime.utcnow()
                    library['updated_at'] = datetime.utcnow()
                    db.equipment_libraries.insert_one(library)
                new_library_ids.append(str(library['_id']))
                processed_equipment_libraries.append(library)

            # 确保每个新元素都有 element_id，并合并设备库参数
            elements = ensure_element_id(elements)
            elements = merge_library_params(elements, processed_equipment_libraries)

            # 使用 $push 追加新数据，而不覆盖原有数据
            db.networks.update_one(
                {"_id": ObjectId(network_id)},
                {
                    "$set": {
                        "simulation_config": simulation_config,
                        "SI": merge_dicts(network.get("SI", {}), SI),
                        "Span": merge_dicts(network.get("Span", {}), Span),
                        "updated_at": datetime.utcnow()
                    },
                    "$push": {
                        "elements": {"$each": elements},
                        "connections": {"$each": connections},
                        "services": {"$each": services},
                        "equipment_library_ids": {"$each": new_library_ids}
                    }
                }
            )

            # 重新查询更新后的网络数据
            updated_network = db.networks.find_one({"_id": ObjectId(network_id)})
            updated_network = convert_objectid_and_datetime(updated_network)

            # 查询所有关联的设备库完整文档（根据最新的 equipment_library_ids 字段）
            all_library_ids = updated_network.get("equipment_library_ids", [])
            equipment_libraries_response = list(
                db.equipment_libraries.find({"_id": {"$in": [ObjectId(x) for x in all_library_ids]}})
            )
            equipment_libraries_response = [convert_objectid_and_datetime(lib) for lib in equipment_libraries_response]
            for lib in equipment_libraries_response:
                lib.pop("user_id", None)

            # 构造返回响应，不对已转换的日期字段调用 strftime（因为它们已经是字符串）
            response = OrderedDict({
                "network_id": str(updated_network["_id"]),
                "network_name": updated_network["network_name"],
                "created_at": updated_network["created_at"],
                "updated_at": updated_network["updated_at"],
                "elements": updated_network.get("elements", []),
                "connections": updated_network.get("connections", []),
                "services": updated_network.get("services", []),
                "simulation_config": simulation_config,
                "SI": merge_dicts(network.get("SI", {}), SI),
                "Span": merge_dicts(network.get("Span", {}), Span),
                "equipment_libraries": equipment_libraries_response
            })

            return Response(
                response=json.dumps(response),
                status=200,
                mimetype='application/json'
            )

        except Exception as e:
            return {"message": str(e)}, 500


