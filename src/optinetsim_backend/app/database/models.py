from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
from src.optinetsim_backend.app.config import Config

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

    @staticmethod
    def delete_by_userid(user_id):
        return db.users.delete_one({"_id": ObjectId(user_id)}).deleted_count > 0

    @staticmethod
    def find_by_userid(user_id):
        return db.users.find_one({"_id": ObjectId(user_id)})

    @staticmethod
    def update_password(user_id, password):
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password": password}}
        )


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
    def add_element(network_id, element):
        return db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {"$push": {"elements": element}}
        )

    @staticmethod
    def update_element(network_id, element_id, element):
        return db.networks.update_one(
            {"_id": ObjectId(network_id), "elements.element_id": element_id},
            {"$set": {"elements.$": element}}
        )

    @staticmethod
    def delete_by_element_id(network_id, element_id):
        # 删除与该 element 相关的连接关系
        db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {"$pull": {"connections": {"from_node": element_id}}}
        )
        db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {"$pull": {"connections": {"to_node": element_id}}}
        )
        return db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {"$pull": {"elements": {"element_id": element_id}}}
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
    def delete_by_user_id(user_id):
        # 删除用户的所有网络并返回删除成功与否
        return db.networks.delete_many({"user_id": ObjectId(user_id)}).deleted_count

    @staticmethod
    def update_simulation_config(network_id, simulation_config):
        return db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {"$set": {"simulation_config": simulation_config}}
        )

    @staticmethod
    def update_spectrum_information(network_id, spectrum_information):
        return db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {"$set": {"SI": spectrum_information}}
        )

    @staticmethod
    def update_span_parameters(network_id, span_parameters):
        return db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {"$set": {"Span": span_parameters}}
        )

    @staticmethod
    def add_connection(network_id, connection_data):
        """向指定网络添加连接关系"""
        return db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {"$push": {"connections": connection_data}}
        )

    @staticmethod
    def update_connection(network_id, connection_id, update_data):
        """更新指定网络的连接关系"""
        return db.networks.update_one(
            {
                "_id": ObjectId(network_id),
                "connections.connection_id": connection_id
            },
            {
                "$set": {
                    "connections.$.from_node": update_data["from_node"],
                    "connections.$.to_node": update_data["to_node"]
                }
            }
        )

    @staticmethod
    def delete_connection(network_id, connection_id):
        """从指定网络删除连接关系"""
        return db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {"$pull": {"connections": {"connection_id": connection_id}}}
        )

    @staticmethod
    def find_element_name_by_id(network_id, element_id):
        """根据 element_id 查找 element 的 name"""
        network = db.networks.find_one(
            {"_id": ObjectId(network_id), "elements.element_id": element_id},
            {"elements.$": 1}  # 只返回匹配的 element
        )
        if network and network["elements"]:
            return network["elements"][0].get("name", None)
        return None

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
    def find_by_type_variety(user_id, library_id, element_type, element_type_variety):
        # 返回器件库中是否存在该类型的器件，存在则返回该器件，否则返回 None
        library = db.equipment_libraries.find_one({"_id": ObjectId(library_id), "user_id": ObjectId(user_id)})
        if library and element_type in library['equipments']:
            return next((e for e in library['equipments'][element_type] if e['type_variety'] == element_type_variety), None)
        return None

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
        return db.equipment_libraries.delete_one({"_id": ObjectId(library_id)})

    @staticmethod
    def delete_by_user_id(user_id):
        return db.equipment_libraries.delete_many({"user_id": ObjectId(user_id)}).deleted_count

    # 新增器件的方法
    @staticmethod
    def add_equipment(library_id, category, equipment):
        # 检查该类别下是否已经存在相同类型的器件
        res = db.equipment_libraries.find_one(
            {"_id": ObjectId(library_id), f"equipments.{category}.type_variety": equipment['type_variety']}
        )
        if res:
            return False

        # 如果没有重复，添加器件到该类别
        db.equipment_libraries.update_one(
            {"_id": ObjectId(library_id)},
            {"$push": {f"equipments.{category}": equipment}}
        )
        return True

    # 更新器件的方法
    @staticmethod
    def update_equipment(library_id, category, type_variety, equipment_update):
        # 更新器件信息
        return db.equipment_libraries.update_one(
            {"_id": ObjectId(library_id), f"equipments.{category}.type_variety": type_variety},
            {"$set": {f"equipments.{category}.$": equipment_update}}
        )

    # 删除器件的方法
    @staticmethod
    def delete_equipment(library_id, category, type_variety):
        return db.equipment_libraries.update_one(
            {"_id": ObjectId(library_id)},
            {"$pull": {f"equipments.{category}": {"type_variety": type_variety}}}
        )
