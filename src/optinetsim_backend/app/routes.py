from flask import Flask, jsonify, request
from flask_restful import Api, Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId
from src.optinetsim_backend.app.models import Network, EquipmentLibrary
from src.optinetsim_backend.app.auth import LoginResource, RegisterResource
from src.optinetsim_backend.app.equipment_library import EquipmentLibraryList, EquipmentLibraryDetail, EquipmentList, EquipmentAddResource, EquipmentUpdateResource, EquipmentDeleteResource


class NetworkList(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        networks = Network.find_by_user_id(user_id)
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
        network_id = Network.create(user_id, network_name)
        return {'network_id': str(network_id.inserted_id)}, 201


class NetworkResource(Resource):
    @jwt_required()  # 添加 JWT 鉴权
    def get(self, network_id):
        user_id = get_jwt_identity()
        network = Network.find_by_network_id(user_id, network_id)
        if network:
            # 返回网络信息
            return {
                "network_id": str(network['_id']),
                "network_name": network['network_name'],
                "created_at": network['created_at'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                "updated_at": network['updated_at'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                "elements": network['elements'],
                "connections": network['connections'],
                "service": network['services'],
                "simulation_config": network['simulation_config']
            }, 200
        return {'message': 'Network not found'}, 404

    @jwt_required()  # 添加 JWT 鉴权
    def put(self, network_id):
        user_id = get_jwt_identity()
        parser = reqparse.RequestParser()
        parser.add_argument('network_name', type=str, required=True)
        args = parser.parse_args()

        network = Network.modify_network_name(user_id, network_id, args['network_name'])
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
        network = Network.delete_by_network_id(user_id, network_id)
        if network:
            return {'message': 'Network deleted successfully'}, 200
        return {'message': 'Network not found'}, 404


def api_init_app(app):
    api = Api(app)

    # 用户认证相关接口
    api.add_resource(LoginResource, '/api/auth/login')
    api.add_resource(RegisterResource, '/api/auth/register')
    api.add_resource(NetworkResource, '/api/networks/<string:network_id>')

    # 器件库相关接口
    api.add_resource(EquipmentLibraryList, '/api/equipment-libraries')
    api.add_resource(EquipmentLibraryDetail, '/api/equipment-libraries/<string:library_id>')

    # 新增器件操作相关接口
    api.add_resource(EquipmentList, '/api/equipment-libraries/<string:library_id>/equipment')
    api.add_resource(EquipmentAddResource, '/api/equipment-libraries/<string:library_id>/equipment/<string:category>')
    api.add_resource(EquipmentUpdateResource,
                     '/api/equipment-libraries/<string:library_id>/equipment/<string:category>/<string:type_variety>')
    api.add_resource(EquipmentDeleteResource,
                     '/api/equipment-libraries/<string:library_id>/equipment/<string:category>/<string:type_variety>')

    api.init_app(app)

    return app
