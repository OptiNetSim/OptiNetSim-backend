from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
from src.optinetsim_backend.app.config import Config
import uuid

client = MongoClient(Config.MONGO_URI)
db = client.optinetsim


class UserDB:
    @staticmethod
    def create(username, password, email):
        user = {
            "username": username,
            "password": password,
            "email": email
        }
        return db.users.insert_one(user)

    @staticmethod
    def find_by_username(username):
        return db.users.find_one({"username": username})


class NetworkDB:
    @staticmethod
    def create(user_id, network_name):
        network = {
            "user_id": ObjectId(user_id),
            "network_name": network_name,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "elements": [],
            "connections": [],
            "services": [],
            "SI": {},
            "Span": {},
            "simulation_config": {}
        }
        return db.networks.insert_one(network)

    @staticmethod
    def modify_network_name(user_id, network_id, network_name):
        db.networks.update_one(
            {"_id": ObjectId(network_id), "user_id": ObjectId(user_id)},
            {
                "$set":
                    {
                        "network_name": network_name,
                        "updated_at": datetime.utcnow()
                    }
            }
        )
        return db.networks.find_one({"_id": ObjectId(network_id), "user_id": ObjectId(user_id)})

    @staticmethod
    def ensure_element_id(elements):
        for element in elements:
            if "element_id" not in element:
                element["element_id"] = str(uuid.uuid4())
        return elements

    @staticmethod
    def add_element(network_id, element):
        return db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {"$push": {"elements": element}}
        )

    @staticmethod
    def update_element(network_id, element_id, element):
        return db.networks.update_one(
            {"_id": ObjectId(network_id), "elements.uid": element_id},
            {"$set": {"elements.$": element}}
        )

    @staticmethod
    def delete_by_element_id(network_id, element_id):
        return db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {"$pull": {"elements": {"uid": element_id}}}
        )

    @staticmethod
    def find_by_user_id(user_id):
        return db.networks.find({"user_id": ObjectId(user_id)})

    @staticmethod
    def find_by_network_id(user_id, network_id):
        return db.networks.find_one({"_id": ObjectId(network_id), "user_id": ObjectId(user_id)})

    @staticmethod
    def delete_by_network_id(user_id, network_id):
        # 删除网络并返回删除成功与否
        return db.networks.delete_one({"_id": ObjectId(network_id), "user_id": ObjectId(user_id)}).deleted_count

    @staticmethod
    def get_existing_element_by_id(element_id):
        return db.networks.find_one({"elements.element_id": element_id})

    @staticmethod
    def update_network(network_id, updates):
        updates["updated_at"] = datetime.utcnow()
        db.networks.update_one({"_id": ObjectId(network_id)}, {"$set": updates})
        return db.networks.find_one({"_id": ObjectId(network_id)})

    @staticmethod
    def create_full_network(user_id, network_data):
        network_data["user_id"] = ObjectId(user_id)
        network_data["created_at"] = datetime.utcnow()
        network_data["updated_at"] = datetime.utcnow()
        result = db.networks.insert_one(network_data)
        network_data["_id"] = result.inserted_id
        return network_data

    @staticmethod
    def append_topology(network_id, new_elements, new_connections, new_services):
        db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {
                "$push": {
                    "elements": {"$each": new_elements},
                    "connections": {"$each": new_connections},
                    "services": {"$each": new_services}
                },
                "$set": {
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return db.networks.find_one({"_id": ObjectId(network_id)})


class EquipmentLibraryDB:
    @staticmethod
    def create(user_id, library_name):
        library = {
            "user_id": ObjectId(user_id),
            "library_name": library_name,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "equipments": {
                "Edfa": [],
                "Fiber": [],
                "RamanFiber": [],
                "Roadm": [],
                "Transceiver": []
            }
        }
        return db.equipment_libraries.insert_one(library)

    @staticmethod
    def find_by_user_id(user_id):
        return db.equipment_libraries.find({"user_id": ObjectId(user_id)})

    @staticmethod
    def find_by_id(library_id):
        return db.equipment_libraries.find_one({"_id": ObjectId(library_id)})

    @staticmethod
    def get_existing_library_by_id(library_id):
        return db.equipment_libraries.find_one({"_id": ObjectId(library_id)})

    @staticmethod
    def find_by_library_ids(library_ids):
        # library_ids 是一个字符串列表
        return list(db.equipment_libraries.find({"_id": {"$in": [ObjectId(x) for x in library_ids]}}))

    @staticmethod
    def find_by_type_variety(user_id, library_id, element_type, element_type_variety):
        # 返回器件库中是否存在该类型的器件，存在则返回该器件，否则返回 None
        library = db.equipment_libraries.find_one({"_id": ObjectId(library_id), "user_id": ObjectId(user_id)})
        if library and element_type in library['equipments']:
            return next((e for e in library['equipments'][element_type] if e['type_variety'] == element_type_variety), None)
        return None

    @staticmethod
    # Helper function: Ensure `library_id` is treated as ObjectId for querying
    def get_library_by_id(library_id_str):
        try:
            return db.equipment_libraries.find_one({"_id": ObjectId(library_id_str)})  # Ensure ObjectId conversion
        except Exception as e:
            return None  # In case ObjectId conversion fails

    @staticmethod
    def update(library_id, library_name):
        return db.equipment_libraries.find_one_and_update(
            {"_id": ObjectId(library_id)},
            {
                "$set": {
                    "library_name": library_name,
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )

    @staticmethod
    def delete(library_id):
        result = db.equipment_libraries.delete_one({"_id": ObjectId(library_id)})
        return result.deleted_count > 0

    # 新增器件的方法
    @staticmethod
    def add_equipment(library_id, category, equipment):
        library = db.equipment_libraries.find_one({"_id": ObjectId(library_id)})

        if not library or category not in library['equipments']:
            return False

        # 检查该类别下是否已经存在相同类型的器件
        existing_equipment = next(
            (e for e in library['equipments'][category] if e['type_variety'] == equipment['type_variety']),
            None
        )

        # 如果已存在相同的器件，返回 False
        if existing_equipment:
            return False

        # 如果没有重复，添加器件到该类别
        library['equipments'][category].append(equipment)

        # 更新器件库
        db.equipment_libraries.update_one(
            {"_id": ObjectId(library_id)},
            {"$set": {"equipments": library['equipments'], "updated_at": datetime.utcnow()}}
        )
        return True

    # 更新器件的方法
    @staticmethod
    def update_equipment(library_id, category, type_variety, params):
        library = db.equipment_libraries.find_one({"_id": ObjectId(library_id)})
        if library and category in library['equipments']:
            equipment = next((e for e in library['equipments'][category] if e['type_variety'] == type_variety), None)
            if equipment:
                equipment['params'] = params
                db.equipment_libraries.update_one(
                    {"_id": ObjectId(library_id)},
                    {"$set": {"equipments": library['equipments'], "updated_at": datetime.utcnow()}}
                )
                return True
        return False

    # 删除器件的方法
    @staticmethod
    def delete_equipment(library_id, category, type_variety):
        library = db.equipment_libraries.find_one({"_id": ObjectId(library_id)})
        if library and category in library['equipments']:
            equipment = next((e for e in library['equipments'][category] if e['type_variety'] == type_variety), None)
            if equipment:
                library['equipments'][category].remove(equipment)
                db.equipment_libraries.update_one(
                    {"_id": ObjectId(library_id)},
                    {"$set": {"equipments": library['equipments'], "updated_at": datetime.utcnow()}}
                )
                return True
        return False

    @staticmethod
    def create_library(library_data, user_id):
        if "library_name" not in library_data:
            raise ValueError("library_name is required in equipment library data")
        if "equipments" not in library_data:
            library_data["equipments"] = {
                "Edfa": [],
                "Fiber": [],
                "RamanFiber": [],
                "Roadm": [],
                "Transceiver": []
            }
        if "_id" in library_data:
            if isinstance(library_data["_id"], str):
                library_data["_id"] = ObjectId(library_data["_id"])
        else:
            library_data["_id"] = ObjectId()
        library_data["user_id"] = ObjectId(user_id)
        library_data["created_at"] = datetime.utcnow()
        library_data["updated_at"] = datetime.utcnow()
        result = db.equipment_libraries.insert_one(library_data)
        return str(result.inserted_id)

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
