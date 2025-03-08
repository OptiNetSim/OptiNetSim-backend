from flask_restful import Resource, reqparse
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from pymongo import MongoClient
from src.optinetsim_backend.app.database.models import NetworkDB
from bson import ObjectId


client = MongoClient("mongodb://localhost:27017/")
db = client.optinetsim
networks_collection = db.networks


class NetworkExportResource(Resource):
    @jwt_required()
    def get(self, network_id):
        try:
            user_id = get_jwt_identity()

            network = networks_collection.find_one({"_id": ObjectId(network_id), "user_id": ObjectId(user_id)})
            if not network:
                return {"message": f"Network with id {network_id} not found or unauthorized."}, 404

            network["_id"] = str(network["_id"])

            topologies_data = []
            for topology in network.get("topologies", []):
                topology_data = {
                    "topology_name": topology.get("topology_name", ""),
                    "elements": topology.get("elements", []),
                    "connections": topology.get("connections", []),
                    "services": topology.get("services", []),
                    "simulation_config": topology.get("simulation_config", {}),
                    "SI": topology.get("SI", {}),
                    "Span": topology.get("Span", {}),
                    "equipment_libraries": topology.get("equipment_libraries", [])
                }
                topologies_data.append(topology_data)

            return jsonify({
                "network_id": network_id,
                "network_name": network.get("network_name", ""),
                "topologies": topologies_data
            })

        except Exception as e:
            return {"message": f"An error occurred: {str(e)}"}, 500


class NetworkImportResource(Resource):
    @jwt_required()
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('network_name', type=str, required=True, help="Network name is required.")
        parser.add_argument('elements', type=list, location='json', required=True, help="Network elements are required.")
        parser.add_argument('connections', type=list, location='json', required=True, help="Network connections are required.")
        parser.add_argument('services', type=list, location='json', required=True, help="Network services are required.")
        parser.add_argument('simulation_config', type=dict, required=True, help="Simulation configuration is required.")
        parser.add_argument('SI', type=dict, required=True, help="Spectrum Information (SI) is required.")
        parser.add_argument('Span', type=dict, required=True, help="Span parameters are required.")
        parser.add_argument('equipment_libraries', type=list, location='json', required=True, help="Equipment libraries are required.")

        try:
            args = parser.parse_args()

            user_id = get_jwt_identity()

            network = {
                "user_id": ObjectId(user_id),
                "network_name": args["network_name"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "elements": args["elements"],
                "connections": args["connections"],
                "services": args["services"],
                "SI": args["SI"],
                "Span": args["Span"],
                "simulation_config": args["simulation_config"],
                "topologies": []
            }

            result = NetworkDB.create(user_id, network["network_name"])

            network_id = str(result.inserted_id)

            topology = {
                "topology_name": "Topology1",  
                "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "elements": args["elements"],
                "connections": args["connections"],
                "services": args["services"],
                "simulation_config": args["simulation_config"],
                "SI": args["SI"],
                "Span": args["Span"],
                "equipment_libraries": args["equipment_libraries"]
            }

            NetworkDB.add_topology(network_id, topology)

            network = NetworkDB.find_by_network_id(user_id, network_id)

            topologies_data = network.get("topologies", [])

            response_data = {
                "network_id": network_id,
                "network_name": args["network_name"],
                "topologies": topologies_data
            }

            return response_data, 201

        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return jsonify({"message": f"An error occurred: {str(e)}"}), 500


class NetworkImportTopologyResource(Resource):
    @jwt_required()
    def post(self, network_id):
        parser = reqparse.RequestParser()
        parser.add_argument('topology_name', type=str, required=True, help="Topology name is required.")
        parser.add_argument('elements', type=list, location='json', required=True, help="Network elements are required.")
        parser.add_argument('connections', type=list, location='json', required=True, help="Network connections are required.")
        parser.add_argument('services', type=list, location='json', required=True, help="Network services are required.")
        parser.add_argument('simulation_config', type=dict, required=True, help="Simulation configuration is required.")
        parser.add_argument('SI', type=dict, required=True, help="Spectrum Information (SI) is required.")
        parser.add_argument('Span', type=dict, required=True, help="Span parameters are required.")
        parser.add_argument('equipment_libraries', type=list, location='json', required=True, help="Equipment libraries are required.")

        try:
            args = parser.parse_args()

            user_id = get_jwt_identity()

            network = NetworkDB.find_by_network_id(user_id, network_id)
            if not network:
                return {"message": f"Network with id {network_id} not found or unauthorized."}, 404

            # 创建拓扑数据
            topology = {
                "topology_name": args["topology_name"],
                "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "elements": args["elements"],
                "connections": args["connections"],
                "services": args["services"],
                "simulation_config": args["simulation_config"],
                "SI": args["SI"],
                "Span": args["Span"],
                "equipment_libraries": args["equipment_libraries"]
            }
 
            NetworkDB.add_topology(network_id, topology)

            response_data = {
                "network_id": network_id,
                "network_name": network.get("network_name", ""),
                "topology_name": args["topology_name"],
                "created_at": topology["created_at"],
                "updated_at": topology["updated_at"],
                "elements": topology["elements"],
                "connections": topology["connections"],
                "services": topology["services"],
                "simulation_config": topology["simulation_config"],
                "SI": topology["SI"],
                "Span": topology["Span"],
                "equipment_libraries": topology["equipment_libraries"]
            }

            return response_data, 201

        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return jsonify({"message": f"An error occurred: {str(e)}"}), 500

