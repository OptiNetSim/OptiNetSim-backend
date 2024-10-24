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
    def find_by_user_id(user_id):
        return db.networks.find({"user_id": ObjectId(user_id)})

    @staticmethod
    def find_by_network_id(user_id, network_id):
        return db.networks.find_one({"_id": ObjectId(network_id), "user_id": ObjectId(user_id)})

    @staticmethod
    def delete_by_network_id(user_id, network_id):
        # 删除网络并返回删除成功与否
        return db.networks.delete_one({"_id": ObjectId(network_id), "user_id": ObjectId(user_id)}).deleted_count
