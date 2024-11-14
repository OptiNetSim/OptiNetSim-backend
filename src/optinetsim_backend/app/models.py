from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
from src.optinetsim_backend.app.config import Config

client = MongoClient(Config.MONGO_URI)
db = client.optinetsim


class User:
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


class Network:
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
            "simulation_config": {}
        }
        return db.networks.insert_one(network)

    @staticmethod
    def find_by_user_id(user_id):
        return db.networks.find({"user_id": ObjectId(user_id)})

class EquipmentLibrary:
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
                "Span": [],
                "Roadm": [],
                "SI": [],
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
