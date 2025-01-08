from flask import request
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity

# Project imports
from src.optinetsim_backend.app.database.models import NetworkDB


class NetworkList(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        networks = NetworkDB.find_by_user_id(user_id)
        networks_list = [
            {
                "network_id": str(network['_id']),
                "network_name": network['network_name'],
                "created_at": network['created_at'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                "updated_at": network['updated_at'].strftime('%Y-%m-%dT%H:%M:%SZ')
            }
            for network in networks
        ]
        return {'networks': networks_list}, 200

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        network_name = request.json.get('network_name', None)
        network = NetworkDB.create(user_id, network_name)
        return {'network_id': str(network.inserted_id)}, 201


class NetworkResource(Resource):
    @jwt_required()  # 添加 JWT 鉴权
    def get(self, network_id):
        user_id = get_jwt_identity()
        networks = NetworkDB.find_by_network_id(user_id, network_id)
        if networks:
            # 返回网络信息
            return {
                "network_id": str(networks['_id']),
                "network_name": networks['network_name'],
                "created_at": networks['created_at'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                "updated_at": networks['updated_at'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                "elements": [
                    {
                        "uid": str(element['uid']),
                        "library_id": element['library_id'],
                        "name": element['name'],
                        "type": element['type'],
                        "type_variety": element['type_variety'],
                        "params": element['params'],
                        "metadata": element['metadata']
                    }
                    for element in networks['elements']
                ],
                "connections": networks['connections'],
                "service": networks['services'],
                "simulation_config": networks['simulation_config']
            }, 200
        return {'message': 'Network not found'}, 404

    @jwt_required()  # 添加 JWT 鉴权
    def put(self, network_id):
        user_id = get_jwt_identity()
        parser = reqparse.RequestParser()
        parser.add_argument('network_name', type=str, required=True)
        args = parser.parse_args()

        network = NetworkDB.modify_network_name(user_id, network_id, args['network_name'])
        if network:
            # 返回网络信息
            return {
                "network_id": str(network['_id']),
                "network_name": network['network_name'],
                "created_at": network['created_at'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                "updated_at": network['updated_at'].strftime('%Y-%m-%dT%H:%M:%SZ')
            }, 200
        return {'message': 'Network not found'}, 404

    @jwt_required()  # 添加 JWT 鉴权
    def delete(self, network_id):
        user_id = get_jwt_identity()
        network = NetworkDB.delete_by_network_id(user_id, network_id)
        if network:
            return {'message': 'Network deleted successfully'}, 200
        return {'message': 'Network not found'}, 404