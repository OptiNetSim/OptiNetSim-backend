import uuid
from flask_restful import Resource
from flask import Response, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from src.optinetsim_backend.app.config import Config
from src.optinetsim_backend.app.database.models import NetworkDB, db, EquipmentLibraryDB
from collections import OrderedDict
import json

client = MongoClient(Config.MONGO_URI)

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
            equipment_libraries = list(db.equipment_libraries.find({"_id": {"$in": [ObjectId(x) for x in library_ids]}}))
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

def insert_equipment_library(library_data, user_id):
    # Insert the library data into the equipment_libraries collection
    library_data["user_id"] = ObjectId(user_id)  # Assign the user_id to the equipment library
    result = db.equipment_libraries.insert_one(library_data)
    return str(result.inserted_id)  # Return the inserted library's _id

def get_existing_element_by_id(element_id):
    return db.networks.find_one({"elements.element_id": element_id})

def get_existing_library_by_id(library_id):
    return db.equipment_libraries.find_one({"_id": ObjectId(library_id)})

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

            inserted_library_ids = []
            for library in equipment_libraries:
                if "_id" in library:
                    existing_library = db.equipment_libraries.find_one({"_id": ObjectId(library["_id"])})
                    if existing_library:
                        db.equipment_libraries.update_one(
                            {"_id": ObjectId(library["_id"])},
                            {"$set": {
                                "library_name": library["library_name"],
                                "created_at": library.get("created_at", datetime.utcnow()),
                                "updated_at": datetime.utcnow(),
                                "equipments": library["equipments"]
                            }}
                        )
                    else:
                        # Library does not exist, insert new one
                        library["_id"] = ObjectId(library["_id"])  # Ensure _id is ObjectId type
                        library["user_id"] = ObjectId(user_id)  # Insert correct user_id
                        library["created_at"] = datetime.utcnow()
                        library["updated_at"] = datetime.utcnow()
                        db.equipment_libraries.insert_one(library)
                    inserted_library_ids.append(library["_id"])
                else:
                    library["_id"] = ObjectId()
                    library["user_id"] = ObjectId(user_id)
                    library["created_at"] = datetime.utcnow()
                    library["updated_at"] = datetime.utcnow()
                    db.equipment_libraries.insert_one(library)
                    inserted_library_ids.append(library["_id"])

            # Step 2: Validate and generate element_id for elements
            for element in elements:
                if "element_id" not in element:
                    element["element_id"] = str(uuid.uuid4())  # Automatically generate element_id

                # If library_id is provided, ensure it's an ObjectId
                if "library_id" in element:
                    element["library_id"] = ObjectId(element["library_id"])

            # Step 3: Create network data
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
                "Span": Span
            }

            # Step 4: Insert the network data
            db.networks.insert_one(network)

            # Step 5: Prepare the response data
            response = {
                "network_id": str(network["_id"]),
                "network_name": network_name,
                "created_at": convert_datetime_to_str(network["created_at"]),
                "updated_at": convert_datetime_to_str(network["updated_at"]),
                "elements": convert_objectid_to_str(elements),
                "connections": connections,
                "services": services,
                "simulation_config": simulation_config,
                "SI": SI,
                "Span": Span,
                "equipment_libraries": []
            }

            # Step 6: Get all relevant equipment libraries based on elements' library_id
            # Find all unique library_id used in elements
            library_ids_in_elements = set([element.get("library_id") for element in elements if "library_id" in element])
            equipment_libraries_info = []
            for library_id in library_ids_in_elements:
                library = db.equipment_libraries.find_one({"_id": ObjectId(library_id)})
                if library:
                    # Ensure all data is included in the response
                    library_data = {
                        "_id": str(library["_id"]),
                        "library_name": library["library_name"],
                        "created_at": convert_datetime_to_str(library["created_at"]),
                        "updated_at": convert_datetime_to_str(library["updated_at"]),
                        "equipments": library["equipments"]
                    }
                    library_data.pop("user_id", None)
                    equipment_libraries_info.append(library_data)

            response["equipment_libraries"] = equipment_libraries_info

            response = convert_datetime_to_str(response)

            return Response(
                response=json.dumps(response),
                status=200,
                mimetype='application/json'
            )

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
            network = db.networks.find_one({"_id": ObjectId(network_id), "user_id": ObjectId(user_id)})
            if not network:
                return {"message": "Network not found or access denied."}, 404

            # Get the request body data
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

            # Process the new equipment libraries and insert them into the database
            # We only need to insert libraries that are associated with new elements
            new_library_ids = []
            for library in request_equipment_libraries:
                if "_id" not in library:
                    # Create new library if no _id
                    library['_id'] = ObjectId()
                else:
                    # Ensure the _id is of type ObjectId
                    if isinstance(library["_id"], str):
                        library["_id"] = ObjectId(library["_id"])

                # Set user_id and timestamps
                library['user_id'] = ObjectId(user_id)
                library['created_at'] = datetime.utcnow()
                library['updated_at'] = datetime.utcnow()

                # Insert the library into the database if not already exists
                db.equipment_libraries.insert_one(library)
                new_library_ids.append(str(library['_id']))

            # Collect all library_ids from existing elements and newly added elements
            all_library_ids = set()
            for elem in network.get("elements", []):
                if "library_id" in elem:
                    all_library_ids.add(str(elem["library_id"]))
            for elem in new_elements:
                if "library_id" in elem:
                    all_library_ids.add(str(elem["library_id"]))

            # Validate and ensure that new elements' library_id are in allowed_library_ids
            validated_new_elements = []
            for element in new_elements:
                if "library_id" in element and str(element["library_id"]) in all_library_ids:
                    validated_new_elements.append(element)

            # Generate element_id for new elements
            validated_new_elements = NetworkDB.ensure_element_id(validated_new_elements)

            # Update network with new elements, connections, and services
            db.networks.update_one(
                {"_id": ObjectId(network_id)},
                {
                    "$set": {
                        "simulation_config": network.get("simulation_config", {}),
                        "SI": network.get("SI", {}),
                        "Span": network.get("Span", {}),
                        "updated_at": datetime.utcnow()
                    },
                    "$push": {
                        "elements": {"$each": validated_new_elements},
                        "connections": {"$each": new_connections},
                        "services": {"$each": new_services}
                    }
                }
            )

            # Fetch updated network data
            updated_network = db.networks.find_one({"_id": ObjectId(network_id)})
            updated_network = convert_objectid_and_datetime(updated_network)

            # Fetch only the equipment libraries related to all the library_ids in the elements
            # Query only the libraries that are actually associated with the elements
            equipment_libraries_response = list(
                db.equipment_libraries.find({"_id": {"$in": [ObjectId(x) for x in all_library_ids]}})
            )

            # Ensure to remove user_id field from response and convert object_ids and datetime to string
            for lib in equipment_libraries_response:
                lib.pop("user_id", None)

            # Ensure that all the libraries are included, even if their content is not complete
            equipment_libraries_response = [convert_objectid_and_datetime(lib) for lib in equipment_libraries_response]

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
                "equipment_libraries": equipment_libraries_response  # All libraries that were associated with the elements
            })

            return Response(
                response=json.dumps(response),
                status=200,
                mimetype='application/json'
            )

        except Exception as e:
            return {"message": str(e)}, 500







