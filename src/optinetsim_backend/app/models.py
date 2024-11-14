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
            "equipment": []  # 假设器件库中有设备列表
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