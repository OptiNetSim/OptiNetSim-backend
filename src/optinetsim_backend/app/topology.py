from flask import request, jsonify
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId
from src.optinetsim_backend.app.models import Network

class AddTopologyElement(Resource):
    @jwt_required()
    def post(self, network_id):
        """添加网络拓扑元素"""
        user_id = get_jwt_identity()
        data = request.get_json()

        network = Network.find_by_id_and_user(network_id, user_id)
        if not network:
            return {"message": "Network not found"}, 404

        new_element = {
            "uid": ObjectId(),
            "name": data["name"],
            "type": data["type"],
            "type_variety": data["type_variety"],
            "params": data["params"],
            "metadata": data["metadata"],
        }
        success = Network.add_element(network_id, new_element)
        if success:
            return jsonify(new_element), 201
        else:
            return {"message": "Failed to add element"}, 400


class DeleteTopologyElement(Resource):
    @jwt_required()
    def delete(self, network_id, element_id):
        """删除网络拓扑元素"""
        user_id = get_jwt_identity()

        network = Network.find_by_id_and_user(network_id, user_id)
        if not network:
            return {"message": "Network not found"}, 404

        success = Network.delete_element(network_id, element_id)
        if success:
            return {"message": "Element deleted successfully"}, 200
        else:
            return {"message": "Element not found"}, 404


class ModifyTopologyInterface(Resource):
    @jwt_required()
    def put(self, network_id, element_id):
        """修改网络拓扑元素"""
        user_id = get_jwt_identity()
        data = request.get_json()

        network = Network.find_by_id_and_user(network_id, user_id)
        if not network:
            return {"message": "Network not found"}, 404

        success = Network.modify_element(network_id, element_id, data)
        if success:
            return jsonify({
                "id": element_id,
                "name": data["name"],
                "type": data["type"],
                "type_variety": data["type_variety"],
                "params": data["params"],
                "metadata": data["metadata"]
            }), 200
        else:
            return {"message": "Failed to update element"}, 404


class ModifyGlobalSimulation(Resource):
    @jwt_required()
    def put(self, network_id):
        """修改仿真全局设定"""
        user_id = get_jwt_identity()
        data = request.get_json()

        network = Network.find_by_id_and_user(network_id, user_id)
        if not network:
            return {"message": "Network not found"}, 404

        success = Network.update_simulation_config(network_id, data)
        if success:
            return jsonify(data), 200
        else:
            return {"message": "Failed to update simulation config"}, 400


class ReadNetworkInterface(Resource):
    @jwt_required()
    def get(self, network_id):
        """读取网络接口"""
        user_id = get_jwt_identity()

        network = Network.find_by_id_and_user(network_id, user_id)
        if not network:
            return {"message": "Network not found"}, 404

        return jsonify(network), 200
