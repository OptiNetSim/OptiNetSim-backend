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

        new_element = {
            "uid": str(ObjectId()),
            "library_id": data["library_id"],
            "name": data["name"],
            "type": data["type"],
            "type_variety": data["type_variety"],
            "params": data["params"],
            "metadata": data["metadata"],
        }
        # 验证指定的 type_variety 在器件库中是否存在
        if not EquipmentLibraryDB.find_by_type_variety(user_id, new_element["library_id"], new_element["type_variety"]):
            return {"message": "Type variety not found in equipment library"}, 404
        res = NetworkDB.add_element(network_id, new_element)
        if res.modified_count > 0:
            return {
                "uid": new_element["uid"],
                "library_id": new_element["library_id"],
                "name": new_element["name"],
                "type": new_element["type"],
                "type_variety": new_element["type_variety"],
                "params": new_element["params"],
                "metadata": new_element["metadata"]
            }, 201
        else:
            return {"message": "Failed to add element"}, 400


class TopologyUpdateElement(Resource):
    @jwt_required()
    def put(self, network_id, element_id):
        """修改网络拓扑元素"""
        user_id = get_jwt_identity()
        data = request.get_json()

        # 向 data 中添加 uid
        data["uid"] = element_id

        network = NetworkDB.find_by_network_id(user_id, network_id)
        if not network:
            return {"message": "Network not found"}, 404

        # 验证指定的 type_variety 在器件库中是否存在
        if not EquipmentLibraryDB.find_by_type_variety(user_id, data["library_id"], data["type_variety"]):
            return {"message": "Type variety not found in equipment library"}, 404

        res = NetworkDB.update_element(network_id, element_id, data)
        if res.modified_count > 0:
            return {
                "uid": element_id,
                "library_id": data["library_id"],
                "name": data["name"],
                "type": data["type"],
                "type_variety": data["type_variety"],
                "params": data["params"],
                "metadata": data["metadata"]
            }, 200
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
