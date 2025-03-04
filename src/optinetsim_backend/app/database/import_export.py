import uuid
from flask_restful import Resource
from flask import Response, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime
from src.optinetsim_backend.app.database.models import NetworkDB, EquipmentLibraryDB
from collections import OrderedDict
import json

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

def merge_dicts(old_dict, new_dict):
    merged = old_dict.copy()
    for key, value in new_dict.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged

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
            # 查找网络数据
            network = NetworkDB.find_by_network_id(user_id, network_id)
            if not network:
                return {"message": "Network not found or access denied."}, 404

            # 转换 ObjectId 和 datetime
            network = convert_objectid_and_datetime(network)
            network.pop("user_id", None)  # 移除 user_id

            # 收集所有元素的 library_id
            library_ids = set()
            for element in network.get("elements", []):
                if "library_id" in element:
                    library_ids.add(element["library_id"])

            # 查询所有设备库，只返回在元素中提到的设备库
            equipment_libraries = EquipmentLibraryDB.find_by_library_ids(list(library_ids))
            equipment_libraries = [convert_objectid_and_datetime(lib) for lib in equipment_libraries]
            for lib in equipment_libraries:
                lib.pop("user_id", None)  # 移除 user_id

            # 确保每个元素都有 element_id
            network["elements"] = NetworkDB.ensure_element_id(network.get("elements", []))

            # 处理设备库内容，确保返回规范化的数据
            for lib in equipment_libraries:
                # 确保设备库中的每个equipment字段有标准格式
                for equipment_type, equipments in lib.get("equipments", {}).items():
                    for equipment in equipments:
                        # 使用字典获取type_variety和params，如果缺少则返回默认值
                        equipment["type_variety"] = equipment.get("type_variety", "Unknown")
                        equipment["params"] = equipment.get("params", {})

            # 构建响应数据
            response = OrderedDict({
                "network_name": network["network_name"],
                "elements": network.get("elements", []),
                "connections": network.get("connections", []),
                "services": network.get("services", []),
                "simulation_config": network.get("simulation_config", {}),
                "SI": network.get("SI", {}),
                "Span": network.get("Span", {}),
                "equipment_libraries": equipment_libraries  # 返回所有与元素关联的设备库
            })

            # 返回响应数据
            return Response(response=json.dumps(response), status=200, mimetype='application/json')

        except Exception as e:
            return {"message": str(e)}, 500

######################################
# NetworkImportResource (新建网络数据)
######################################

def generate_element_id():
    return str(ObjectId())

# Helper function: Validate elements' type and type_variety
def validate_elements(elements, equipment_libraries):
    valid_types = ["Edfa", "Fiber", "RamanFiber", "Span", "Roadm", "Transceiver"]
    for element in elements:
        # Validate type
        if element["type"] not in valid_types:
            raise ValueError(f"Invalid type: {element['type']}. Valid types are {', '.join(valid_types)}.")

        # Check if the type_variety exists in the corresponding equipment library
        library = EquipmentLibraryDB.get_library_by_id(element["library_id"])  # Fetch the library using ObjectId
        if library:
            valid_type_varieties = [eq["type_variety"] for eq in library["equipments"].get(element["type"], [])]
            if element["type_variety"] not in valid_type_varieties:
                raise ValueError(f"Invalid type_variety: {element['type_variety']} for type {element['type']}.")
        else:
            raise ValueError(f"Library with ID {element['library_id']} not found.")
    return elements

# Helper function: Merge parameters from the equipment library to elements
def merge_library_params(elements, equipment_libraries):
    for element in elements:
        library_id = element.get("library_id")
        if library_id:
            library = EquipmentLibraryDB.get_library_by_id(library_id)
            if library:
                equipment = next(
                    (eq for eq in library["equipments"].get(element["type"], []) if
                     eq["type_variety"] == element["type_variety"]),
                    None
                )
                if equipment:
                    element["params"] = equipment["params"]
                    if "params" in element:
                        element["params"].update(element["params"])

    return elements

def convert_objectid_to_str(obj):
    if isinstance(obj, dict):
        return {k: convert_objectid_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    return obj

def convert_datetime_to_str(obj):
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(obj, dict):
        return {k: convert_datetime_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_str(item) for item in obj]
    return obj

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

            # 处理设备库：调用模型层方法插入或更新设备库，返回插入后的 _id（字符串形式）
            inserted_library_ids = []
            for library in equipment_libraries:
                if "_id" in library:
                    existing_library = EquipmentLibraryDB.find_by_id(library["_id"])
                    if existing_library:
                        EquipmentLibraryDB.update(library["_id"], {
                            "library_name": library["library_name"],
                            "equipments": library["equipments"],
                            "created_at": library.get("created_at", datetime.utcnow())
                        })
                        inserted_library_ids.append(str(library["_id"]))
                    else:
                        inserted_library_ids.append(EquipmentLibraryDB.create_library(library, user_id))
                else:
                    inserted_library_ids.append(EquipmentLibraryDB.create_library(library, user_id))

            # 处理 elements：确保每个元素都有 element_id，并将 library_id 保持为字符串
            for element in elements:
                if "element_id" not in element:
                    element["element_id"] = str(uuid.uuid4())
                if "library_id" in element:
                    element["library_id"] = str(element["library_id"])
            elements = NetworkDB.ensure_element_id(elements)

            # 组装完整的网络数据
            network_data = {
                "network_name": network_name,
                "elements": elements,
                "connections": connections,
                "services": services,
                "simulation_config": simulation_config,
                "SI": SI,
                "Span": Span
            }
            # 调用模型层方法创建网络，返回完整网络文档
            network = NetworkDB.create_full_network(user_id, network_data)

            # 构造响应数据
            response = {
                "network_id": str(network["_id"]),
                "network_name": network["network_name"],
                "created_at": convert_datetime_to_str(network["created_at"]),
                "updated_at": convert_datetime_to_str(network["updated_at"]),
                "elements": convert_objectid_to_str(network["elements"]),
                "connections": network.get("connections", []),
                "services": network.get("services", []),
                "simulation_config": network.get("simulation_config", {}),
                "SI": network.get("SI", {}),
                "Span": network.get("Span", {}),
                "equipment_libraries": []  # 稍后填充
            }

            # 仅返回与 elements 关联的设备库：提取所有元素中的 library_id
            library_ids_in_elements = set([element.get("library_id") for element in elements if "library_id" in element])
            equipment_libraries_info = EquipmentLibraryDB.find_by_library_ids(list(library_ids_in_elements))
            equipment_libraries_info = [convert_objectid_and_datetime(lib) for lib in equipment_libraries_info]
            for lib in equipment_libraries_info:
                lib.pop("user_id", None)
            response["equipment_libraries"] = equipment_libraries_info

            response = convert_datetime_to_str(response)
            return Response(response=json.dumps(response), status=200, mimetype="application/json")
        except Exception as e:
            return {"message": str(e)}, 500

######################################
# TopologyImportResource (插入拓扑)
######################################

class TopologyImportResource(Resource):
    @jwt_required()
    def post(self, network_id):
        try:
            user_id = get_jwt_identity()
            # 使用模型层方法查找网络数据
            network = NetworkDB.find_by_network_id(user_id, network_id)
            if not network:
                return {"message": "Network not found or access denied."}, 404

            # 获取请求参数
            data = request.get_json()
            if not data:
                return {"message": "Invalid request body"}, 400

            new_elements = data.get("elements", [])
            new_connections = data.get("connections", [])
            new_services = data.get("services", [])
            simulation_config = data.get("simulation_config", {})
            SI = data.get("SI", {})
            Span = data.get("Span", {})
            request_equipment_libraries = data.get("equipment_libraries", [])

            # 处理请求中传入的设备库：调用模型层方法插入（或更新）设备库
            new_library_ids = []
            for library in request_equipment_libraries:
                # 如果请求中提供了 _id（可能为字符串），确保转换为字符串的 ObjectId
                if "_id" in library:
                    # 如果已存在则更新，否则插入
                    existing = EquipmentLibraryDB.find_by_id(library["_id"])
                    if existing:
                        EquipmentLibraryDB.update(library["_id"], {
                            "library_name": library["library_name"],
                            "equipments": library["equipments"],
                            "created_at": library.get("created_at", datetime.utcnow())
                        })
                        new_library_ids.append(str(library["_id"]))
                    else:
                        new_library_ids.append(EquipmentLibraryDB.create_library(library, user_id))
                else:
                    new_library_ids.append(EquipmentLibraryDB.create_library(library, user_id))

            # 收集所有 library_id：从原有网络中与新元素中提取
            all_library_ids = set()
            for elem in network.get("elements", []):
                if "library_id" in elem:
                    all_library_ids.add(str(elem["library_id"]))
            for elem in new_elements:
                if "library_id" in elem:
                    all_library_ids.add(str(elem["library_id"]))

            # 验证 new_elements 中的 library_id 存在于 all_library_ids
            validated_new_elements = []
            for element in new_elements:
                if "library_id" in element and str(element["library_id"]) in all_library_ids:
                    validated_new_elements.append(element)
            validated_new_elements = NetworkDB.ensure_element_id(validated_new_elements)

            # 使用模型层方法追加拓扑（新元素、连接、服务）到网络中
            updated_network = NetworkDB.append_topology(network_id, validated_new_elements, new_connections, new_services)
            updated_network = convert_objectid_and_datetime(updated_network)

            # 从更新后的网络中提取所有实际使用的 library_id
            library_ids_in_elements = set()
            for elem in updated_network.get("elements", []):
                if "library_id" in elem:
                    library_ids_in_elements.add(str(elem["library_id"]))

            # 查询设备库（仅返回与 elements 关联的库）
            equipment_libraries_response = EquipmentLibraryDB.find_by_library_ids(list(library_ids_in_elements))
            equipment_libraries_response = [convert_objectid_and_datetime(lib) for lib in equipment_libraries_response]
            for lib in equipment_libraries_response:
                lib.pop("user_id", None)

            response = OrderedDict({
                "network_id": str(updated_network["_id"]),
                "network_name": updated_network["network_name"],
                "created_at": updated_network["created_at"],
                "updated_at": updated_network["updated_at"],
                "elements": updated_network.get("elements", []),
                "connections": updated_network.get("connections", []),
                "services": updated_network.get("services", []),
                "simulation_config": updated_network["simulation_config"],
                "SI": updated_network["SI"],
                "Span": updated_network["Span"],
                "equipment_libraries": equipment_libraries_response
            })

            return Response(
                response=json.dumps(response),
                status=200,
                mimetype='application/json'
            )
        except Exception as e:
            return {"message": str(e)}, 500







