from flask import request
from flask_restful import Resource, reqparse

# Project imports
from src.optinetsim_backend.app.database.models import NetworkDB


class NetworkList(Resource):
    @staticmethod
    def get(self):
        networks = NetworkDB.fetch_networks()
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

    @staticmethod
    def post(self):
        network_name = request.json.get('network_name', None)
        network = NetworkDB.create_network(network_name)
        return {
            'network_id': str(network.inserted_id),
            'network_name': network_name,
            'created_at': network.inserted_id.generation_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }, 201


class NetworkResource(Resource):
    @staticmethod
    def get(self, network_id):
        networks = NetworkDB.find_by_network_id(network_id)
        # 若无法找到网络，则返回 404
        if not networks:
            return {'message': 'Network not found'}, 404
        # ObjectId 转换为字符串
        networks['_id'] = str(networks['_id'])
        # 时间格式转换
        networks['created_at'] = networks['created_at'].strftime('%Y-%m-%dT%H:%M:%SZ')
        networks['updated_at'] = networks['updated_at'].strftime('%Y-%m-%dT%H:%M:%SZ')
        if networks:
            # 返回网络信息
            return networks, 200
        return {'message': 'Network not found'}, 404

    @staticmethod
    def put(self, network_id):
        parser = reqparse.RequestParser()
        parser.add_argument('network_name', type=str, required=True)
        args = parser.parse_args()

        network = NetworkDB.modify_network_name(network_id, args['network_name'])
        if network:
            # 返回网络信息
            return {
                "network_id": str(network['_id']),
                "network_name": network['network_name'],
                "created_at": network['created_at'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                "updated_at": network['updated_at'].strftime('%Y-%m-%dT%H:%M:%SZ')
            }, 200
        return {'message': 'Network not found'}, 404

    @staticmethod
    def delete(self, network_id):
        network = NetworkDB.delete_by_network_id(network_id)
        if network:
            return {'message': 'Network deleted successfully'}, 200
        return {'message': 'Network not found'}, 404
