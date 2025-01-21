from flask import request, jsonify
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId

# Project imports
from src.optinetsim_backend.app.database.models import NetworkDB, EquipmentLibraryDB


class TopologyAddElement(Resource):
    @jwt_required()
    def post(self, network_id):
        """添加网络拓扑元素"""
        user_id = get_jwt_identity()
        data = request.get_json()

        network = NetworkDB.find_by_network_id(user_id, network_id)
        if not network:
            return {"message": "Network not found"}, 404

        # 生成 element_id
        data["element_id"] = str(ObjectId())

        # 重新组织数据，使 element_id 位于首个位置
        data = dict({"element_id": data["element_id"]}, **data)

        res = NetworkDB.add_element(network_id, data)
        if res.modified_count > 0:
            return data, 201
        else:
            return {"message": "Failed to add element"}, 400


class TopologyUpdateElement(Resource):
    @jwt_required()
    def put(self, network_id, element_id):
        """修改网络拓扑元素"""
        user_id = get_jwt_identity()
        data = request.get_json()

        # 向 data 中添加 uid
        data["element_id"] = element_id

        # 重新组织数据，使 element_id 位于首个位置
        data = dict({"element_id": data["element_id"]}, **data)

        network = NetworkDB.find_by_network_id(user_id, network_id)
        if not network:
            return {"message": "Network not found"}, 404

        res = NetworkDB.update_element(network_id, element_id, data)
        if res.modified_count > 0:
            return data, 200
        elif res.matched_count != 0:
            return {"message": "No changes detected"}, 200
        else:
            return {"message": "Failed to update element"}, 404


class TopologyDeleteElement(Resource):
    @jwt_required()
    def delete(self, network_id, element_id):
        """删除网络拓扑元素"""
        user_id = get_jwt_identity()

        network = NetworkDB.find_by_network_id(user_id, network_id)
        if not network:
            return {"message": "Network not found"}, 404

        res = NetworkDB.delete_by_element_id(network_id, element_id)
        if res.modified_count > 0:
            return {"message": "Element deleted successfully"}, 200
        else:
            return {"message": "Element not found"}, 404
