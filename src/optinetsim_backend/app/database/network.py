from flask import request
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity


# Project imports
from src.optinetsim_backend.app.database.models import NetworkDB, convert_objectid_and_datetime


class NetworkList(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        networks = NetworkDB.find_by_user_id(user_id)
        networks_list = [
            {
                "network_id": str(network['_id']),
                "network_name": network['network_name'],
                "created_at": network['created_at'],
                "updated_at": network['updated_at'],
            }
            for network in networks
        ]
        return {'networks': networks_list}, 200

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        # 从请求 JSON 中获取 "Network name" 字段
        network_name = request.json.get('network_name', None)

        # 若未提供或值为 "null"，返回 400 错误
        if not network_name or network_name.lower() == "null":
            return {'message': 'Network name is required'}, 400

        # 调用模型层方法查找指定 network_name 的网络
        network = NetworkDB.find_by_network_name(network_name)
        if not network:
            return {'message': 'Network not found'}, 404

        # 将 _id 转为字符串，并将 created_at 格式化为 ISO 风格
        network_id_str = str(network['_id'])
        created_at_str = network['created_at'].strftime('%Y-%m-%dT%H:%M:%SZ')

        return {
            "network_id": network_id_str,
            "network_name": network["network_name"],
            "created_at": created_at_str
        }, 200

class NetworkResource(Resource):
    @jwt_required()
    def get(self, network_id):
        user_id = get_jwt_identity()
        network = NetworkDB.find_by_network_id(user_id, network_id)
        if network:
            network = convert_objectid_and_datetime(network)
            return network, 200
        return {'message': 'Network not found'}, 404

    @jwt_required()
    def put(self, network_id):
        user_id = get_jwt_identity()
        parser = reqparse.RequestParser()
        parser.add_argument('network_name', type=str, required=True)
        args = parser.parse_args()

        network = NetworkDB.modify_network_name(user_id, network_id, args['network_name'])
        if network:
            network = convert_objectid_and_datetime(network)
            return {
                "network_id": network['_id'],
                "network_name": network['network_name'],
                "created_at": network['created_at'],
                "updated_at": network['updated_at']
            }, 200
        return {'message': 'Network not found'}, 404

    @jwt_required()
    def delete(self, network_id):
        user_id = get_jwt_identity()
        result = NetworkDB.delete_by_network_id(user_id, network_id)
        if result:
            return {'message': 'Network deleted successfully'}, 200
        return {'message': 'Network not found'}, 404