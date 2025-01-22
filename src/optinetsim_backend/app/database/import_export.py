from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from pymongo import MongoClient
from datetime import datetime

client = MongoClient("mongodb://localhost:27017/")
db = client["optinetsim"]  # 数据库名称
networks_collection = db["networks"]  # 集合名称，用于存储网络数据
equipment_libraries_collection = db["equipment_libraries"]  # 集合名称，用于存储器件库数据

class NetworkExportResource(Resource):
    # 导出指定网络的详细信息，包括器件库
    @jwt_required()  # JWT鉴权
    def get(self, network_id):
        # 确保 network_id 是有效的 ObjectId 格式
        if not ObjectId.is_valid(network_id):
            return {"message": "Invalid network ID f_valid(network_id):ormat."}, 400

        try:
            # 查找指定网络的信息
            network = networks_collection.find_one({"_id": ObjectId(network_id)})
            if not network:
                return {"message": f"Network {network_id} not found."}, 404

            # 查找网络中使用的器件库信息
            equipment_libraries = []
            for library_id in network.get("equipment_libraries", []):
                library = equipment_libraries_collection.find_one({"_id": ObjectId(library_id)})
                if library:
                    equipment_libraries.append({
                        "library_name": library.get("library_name"),
                        "equipments": library.get("equipments")
                    })

            # 构建导出的网络信息
            exported_network = {
                "network_name": network["network_name"],
                "elements": network.get("elements", []),
                "connections": network.get("connections", []),
                "services": network.get("services", []),
                "simulation_config": network.get("simulation_config", {}),
                "SI": network.get("SI", {}),
                "Span": network.get("Span", {}),
                "equipment_libraries": equipment_libraries
            }

            # 返回导出的网络信息
            return exported_network, 200

        except Exception as e:
            return {"message": "An error occurred: " + str(e)}, 500


class NetworkImportResource(Resource):
    # 导入网络到系统
    @jwt_required()  # JWT鉴权
    def post(self):
        # 获取当前用户的身份信息（用户ID）
        current_user_id = get_jwt_identity()

        # 定义请求参数解析器
        parser = reqparse.RequestParser()
        parser.add_argument('network_name', type=str, required=True, help="Network name is required.")
        parser.add_argument('elements', type=list, location='json', required=True, help="Elements are required.")
        parser.add_argument('connections', type=list, location='json', required=True, help="Connections are required.")
        parser.add_argument('services', type=list, location='json', required=True, help="Services are required.")
        parser.add_argument('simulation_config', type=dict, required=True, help="Simulation config is required.")
        parser.add_argument('SI', type=dict, required=True, help="Spectrum information is required.")
        parser.add_argument('Span', type=dict, required=True, help="Span parameters are required.")
        parser.add_argument('equipment_libraries', type=list, location='json', required=True,
                            help="Equipment libraries are required.")

        # 解析请求体参数
        args = parser.parse_args()

        try:
            # 将equipment_libraries中的名字转换为ObjectId
            equipment_libraries_ids = []
            for library_name in args['equipment_libraries']:
                # 假设equipment_libraries_collection是你存储器件库信息的集合
                library = equipment_libraries_collection.find_one({"library_name": library_name})
                if library:
                    equipment_libraries_ids.append(library["_id"])  # 取出器件库的ObjectId
                else:
                    return {"message": f"Library '{library_name}' not found."}, 404

            # 创建网络对象并插入数据库
            network_data = {
                "user_id": current_user_id,  # 使用当前用户的ID
                "network_name": args['network_name'],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "elements": args['elements'],
                "connections": args['connections'],
                "services": args['services'],
                "simulation_config": args['simulation_config'],
                "SI": args['SI'],
                "Span": args['Span'],
                "equipment_libraries": equipment_libraries_ids  # 存储的是ObjectId
            }

            # 插入新网络数据到数据库
            result = networks_collection.insert_one(network_data)

            # 构建响应数据
            response = {
                "network_id": str(result.inserted_id),
                "network_name": args['network_name'],
                "created_at": network_data["created_at"].strftime("%Y-%m-%d %H:%M"),
                "updated_at": network_data["updated_at"].strftime("%Y-%m-%d %H:%M"),
                "elements": args['elements'],
                "connections": args['connections'],
                "services": args['services'],
                "simulation_config": args['simulation_config'],
                "SI": args['SI'],
                "Span": args['Span'],
                "equipment_libraries": equipment_libraries_ids  # 返回的是ObjectId
            }

            # 返回导入的网络信息
            return response, 201

        except Exception as e:
            return {"message": "An error occurred: " + str(e)}, 500


class NetworkImportTopologyResource(Resource):
    # 插入拓扑到现有网络
    @jwt_required()  # JWT鉴权
    def post(self, network_id):
        # 获取当前用户的身份信息（用户ID）
        current_user_id = get_jwt_identity()

        # 确保 network_id 是有效的 ObjectId 格式
        if not ObjectId.is_valid(network_id):
            return {"message": "Invalid network ID format."}, 400

        # 定义请求参数解析器
        parser = reqparse.RequestParser()
        parser.add_argument('elements', type=list, location='json', required=True, help="Elements are required.")
        parser.add_argument('connections', type=list, location='json', required=True, help="Connections are required.")
        parser.add_argument('services', type=list, location='json', required=True, help="Services are required.")
        parser.add_argument('simulation_config', type=dict, required=True, help="Simulation config is required.")
        parser.add_argument('SI', type=dict, required=True, help="Spectrum information is required.")
        parser.add_argument('Span', type=dict, required=True, help="Span parameters are required.")
        parser.add_argument('equipment_libraries', type=list, location='json', required=True,
                            help="Equipment libraries are required.")

        # 解析请求体参数
        args = parser.parse_args()

        try:
            # 查找指定网络的信息
            network = networks_collection.find_one({"_id": ObjectId(network_id)})
            if not network:
                return {"message": f"Network {network_id} not found."}, 404

            # 合并拓扑数据
            updated_network = {
                "network_name": network["network_name"],
                "created_at": network["created_at"],  # 保留原创建时间
                "updated_at": datetime.utcnow(),  # 更新为当前时间
                "elements": network["elements"] + args['elements'],  # 合并elements
                "connections": network["connections"] + args['connections'],  # 合并connections
                "services": network["services"] + args['services'],  # 合并services
                "simulation_config": {**network["simulation_config"], **args['simulation_config']},  # 合并simulation_config
                "SI": {**network["SI"], **args['SI']},  # 合并SI
                "Span": {**network["Span"], **args['Span']},  # 合并Span
                "equipment_libraries": network["equipment_libraries"] + args['equipment_libraries']  # 合并equipment_libraries
            }

            # 更新网络拓扑
            networks_collection.update_one(
                {"_id": ObjectId(network_id)},
                {"$set": updated_network}
            )

            # 返回更新后的网络信息
            return {
                "network_id": network_id,
                "network_name": updated_network["network_name"],
                "created_at": updated_network["created_at"].strftime("%Y-%m-%d %H:%M"),
                "updated_at": updated_network["updated_at"].strftime("%Y-%m-%d %H:%M"),
                "elements": updated_network["elements"],
                "connections": updated_network["connections"],
                "services": updated_network["services"],
                "simulation_config": updated_network["simulation_config"],
                "SI": updated_network["SI"],
                "Span": updated_network["Span"],
                "equipment_libraries": updated_network["equipment_libraries"]
            }, 200

        except Exception as e:
            return {"message": "An error occurred: " + str(e)}, 500
