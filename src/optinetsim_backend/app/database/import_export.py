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

def ensure_element_id(elements):
    for element in elements:
        if "element_id" not in element:
            element["element_id"] = str(uuid.uuid4())
    return elements

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
            network["elements"] = ensure_element_id(network.get("elements", []))

            # 构建响应数据
            response = OrderedDict({
                "network_name": network["network_name"],
                "elements": network.get("elements", []),
                "connections": network.get("connections", []),
                "services": network.get("services", []),
                "simulation_config": network.get("simulation_config", {}),
                "SI": network.get("SI", {}),
                "Span": network.get("Span", {}),
                "equipment_libraries": equipment_libraries  # 只返回与元素关联的设备库
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

# Helper function: Ensure `library_id` is treated as ObjectId for querying
def get_library_by_id(library_id_str):
    try:
        return db.equipment_libraries.find_one({"_id": ObjectId(library_id_str)})  # Ensure ObjectId conversion
    except Exception as e:
        return None  # In case ObjectId conversion fails

# Helper function: Validate elements' type and type_variety
def validate_elements(elements, equipment_libraries):
    valid_types = ["Edfa", "Fiber", "RamanFiber", "Span", "Roadm", "Transceiver"]
    for element in elements:
        # Validate type
        if element["type"] not in valid_types:
            raise ValueError(f"Invalid type: {element['type']}. Valid types are {', '.join(valid_types)}.")

        # Check if the type_variety exists in the corresponding equipment library
        library = get_library_by_id(element["library_id"])  # Fetch the library using ObjectId
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
            # Find the equipment library based on library_id
            library = get_library_by_id(library_id)
            if library:
                equipment = next(
                    (eq for eq in library["equipments"].get(element["type"], []) if
                     eq["type_variety"] == element["type_variety"]),
                    None
                )
                if equipment:
                    # Merge the parameters from the library into the element
                    # Only merge the params fields that are relevant and don't introduce unexpected fields
                    element["params"] = equipment["params"]  # Overwrite params from the library
                    # Now merge any additional params from the element itself (if present)
                    if "params" in element:
                        element["params"].update(element["params"])

    return elements

# Helper function to convert ObjectId to string recursively
def convert_objectid_to_str(obj):
    if isinstance(obj, dict):
        return {k: str(v) if isinstance(v, ObjectId) else v for k, v in obj.items()}
    elif isinstance(obj, list):
        return [str(item) if isinstance(item, ObjectId) else item for item in obj]
    return obj

# Helper function to convert datetime to string
def convert_datetime_to_str(obj):
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d %H:%M:%S")  # Convert datetime to string format
    if isinstance(obj, dict):
        return {k: convert_datetime_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_str(item) for item in obj]
    return obj

# Main resource to handle network import
# Helper function: Insert equipment library into the database
def insert_equipment_library(library_data, user_id):
    # Insert the library data into the equipment_libraries collection
    library_data["user_id"] = ObjectId(user_id)  # Assign the user_id to the equipment library
    result = db.equipment_libraries.insert_one(library_data)
    return str(result.inserted_id)  # Return the inserted library's _id

# Main resource to handle network import

class NetworkImportResource(Resource):
    @jwt_required()
    def post(self):
        try:
            user_id = get_jwt_identity()  # Get the user_id from the JWT token
            data = request.get_json()

            if not data:
                return {"message": "Invalid request body"}, 400

            # Extract network information from the request
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

            # Step 1: Validate elements' type and type_variety
            elements = validate_elements(elements, equipment_libraries)

            # Step 2: Generate element_id for each element
            for element in elements:
                element["element_id"] = generate_element_id()

            # Step 3: Create network data
            network = {
                "user_id": ObjectId(user_id),  # Ensure the user_id is stored as ObjectId
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

            # Insert the new network document into the database
            db.networks.insert_one(network)

            # Step 4: Construct the response data (directly from the request parameters)
            response = {
                "network_id": str(network["_id"]),  # Convert ObjectId to string
                "network_name": network_name,
                "created_at": convert_datetime_to_str(network["created_at"]),  # Convert datetime to string
                "updated_at": convert_datetime_to_str(network["updated_at"]),  # Convert datetime to string
                "elements": convert_objectid_to_str(elements),  # Convert ObjectId in elements
                "connections": connections,
                "services": services,
                "simulation_config": simulation_config,
                "SI": SI,
                "Span": Span,
                "equipment_libraries": []  # Empty at first, will be populated below
            }

            # Fetch equipment libraries from the database and add them to the response
            equipment_libraries = [
                convert_objectid_to_str(lib) for lib in db.equipment_libraries.find({"_id": {"$in": [ObjectId(x) for x in [element['library_id'] for element in elements]]}})
            ]
            response["equipment_libraries"] = equipment_libraries

            # Ensure all datetime objects are converted to string before returning
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

            # Process the new equipment libraries
            allowed_library_ids = set()
            for elem in network.get("elements", []):
                if "library_id" in elem:
                    allowed_library_ids.add(str(elem["library_id"]))
                if "associated_library_ids" in elem:
                    allowed_library_ids.update([str(lib_id) for lib_id in elem["associated_library_ids"]])

            # Process and add new equipment libraries
            new_library_ids = []
            for library in request_equipment_libraries:
                if "_id" not in library:
                    # Create new library if no _id
                    library['_id'] = ObjectId()
                    library['user_id'] = ObjectId(user_id)
                    library['created_at'] = datetime.utcnow()
                    library['updated_at'] = datetime.utcnow()
                    db.equipment_libraries.insert_one(library)
                    library.pop('user_id', None)  # Remove user_id field
                    new_library_ids.append(str(library['_id']))
                else:
                    # If library has _id, make sure it's in allowed_library_ids
                    if str(library["_id"]) in allowed_library_ids:
                        new_library_ids.append(str(library["_id"]))

            # Merge new libraries with the existing allowed libraries
            allowed_library_ids = list(set(allowed_library_ids) | set(new_library_ids))

            # Validate and ensure that new elements' library_id are in allowed_library_ids
            validated_new_elements = []
            for element in new_elements:
                if "library_id" in element and str(element["library_id"]) in allowed_library_ids:
                    element["associated_library_ids"] = allowed_library_ids
                    validated_new_elements.append(element)
            new_elements = ensure_element_id(validated_new_elements)  # Ensure each element has an element_id

            # Add new topology data (elements, connections, services)
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
                        "elements": {"$each": new_elements},
                        "connections": {"$each": new_connections},
                        "services": {"$each": new_services}
                    }
                }
            )

            # Fetch updated network data
            updated_network = db.networks.find_one({"_id": ObjectId(network_id)})
            updated_network = convert_objectid_and_datetime(updated_network)

            # Fetch equipment libraries related to the elements in the network
            # Only return libraries that are associated with elements
            equipment_libraries_response = list(
                db.equipment_libraries.find({"_id": {"$in": [ObjectId(x) for x in allowed_library_ids]}})
            )
            equipment_libraries_response = [convert_objectid_and_datetime(lib) for lib in equipment_libraries_response]
            for lib in equipment_libraries_response:
                lib.pop("user_id", None)

            # Prepare the response data
            response = OrderedDict({
                "network_id": str(updated_network["_id"]),
                "network_name": updated_network["network_name"],
                "created_at": updated_network["created_at"],
                "updated_at": updated_network["updated_at"],
                "elements": updated_network.get("elements", []),
                "connections": updated_network.get("connections", []),
                "services": updated_network.get("services", []),
                "simulation_config": updated_network["simulation_config"],  # Keep original simulation_config
                "SI": updated_network["SI"],  # Keep original SI
                "Span": updated_network["Span"],  # Keep original Span
                "equipment_libraries": equipment_libraries_response  # Return only relevant equipment libraries
            })

            return Response(
                response=json.dumps(response),
                status=200,
                mimetype='application/json'
            )

        except Exception as e:
            return {"message": str(e)}, 500


