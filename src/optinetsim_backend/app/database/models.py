# src/optinetsim_backend/app/database/models.py
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
from src.optinetsim_backend.app.config import Config

client = MongoClient(Config.MONGO_URI)
db = client.optinetsim


class NetworkDB:
    @staticmethod
    def create_network(network_name):
        network = {
            "network_name": network_name,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "elements": [],
            "connections": [],
            "services": [],  # Ensure 'services' array exists
            "SI": {},
            "Span": {},
            "simulation_config": {}
        }
        return db.networks.insert_one(network)

    @staticmethod
    def modify_network_name(network_id, network_name):
        db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {
                "$set":
                    {
                        "network_name": network_name,
                        "updated_at": datetime.utcnow()
                    }
            }
        )
        return db.networks.find_one({"_id": ObjectId(network_id)})

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
        # 删除与该 element 相关的业务流量要求 (source 或 target)
        db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {"$pull": {"services": {"source_element_id": element_id}}}
        )
        db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {"$pull": {"services": {"target_element_id": element_id}}}
        )
        return db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {"$pull": {"elements": {"element_id": element_id}}}
        )

    @staticmethod
    def fetch_networks():
        return db.networks.find()

    @staticmethod
    def find_by_network_id(network_id):
        return db.networks.find_one({"_id": ObjectId(network_id)})

    @staticmethod
    def delete_by_network_id(network_id):
        # 删除网络并返回删除成功与否
        return db.networks.delete_one({"_id": ObjectId(network_id)}).deleted_count

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

    @staticmethod
    def add_service_requirement(network_id, service_data):
        """
        向指定网络添加业务流量要求
        service_data 包含 source_element_id, target_element_id, traffic_requirement, service_constraints
        """
        # Generate a unique service_id
        service_id = str(ObjectId())
        service_data["service_id"] = service_id

        return db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {
                "$push": {"services": service_data},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

    @staticmethod
    def update_service_requirement(network_id, service_id, traffic_requirement_data):
        """
        更新指定网络的业务流量要求
        traffic_requirement_data 包含 bandwidth 和 latency
        """
        set_fields = {
            "services.$.traffic_requirement.bandwidth": traffic_requirement_data["bandwidth"],
            "services.$.traffic_requirement.latency": traffic_requirement_data["latency"],
            "updated_at": datetime.utcnow()
        }

        return db.networks.update_one(
            {"_id": ObjectId(network_id), "services.service_id": service_id},
            {"$set": set_fields}
        )

    @staticmethod
    def delete_service_requirement(network_id, service_id):
        """
        从指定网络删除业务流量要求
        """
        return db.networks.update_one(
            {"_id": ObjectId(network_id)},
            {
                "$pull": {"services": {"service_id": service_id}},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )


class EquipmentLibraryDB:
    @staticmethod
    def create_library(library_name):
        library = {
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
    def fetch_libraries():
        return db.equipment_libraries.find()

    @staticmethod
    def find_library_by_id(library_id):
        return db.equipment_libraries.find_one({"_id": ObjectId(library_id)})

    @staticmethod
    def find_equipment_by_type_variety(library_id, element_type, element_type_variety):
        # 返回器件库中是否存在该类型的器件，存在则返回该器件，否则返回 None
        library = db.equipment_libraries.find_one({"_id": ObjectId(library_id)})
        if library and element_type in library['equipments']:
            return next((e for e in library['equipments'][element_type] if e['type_variety'] == element_type_variety),
                        None)
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
