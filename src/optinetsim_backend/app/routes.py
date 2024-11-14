from flask import request, jsonify
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from bson import ObjectId
from src.optinetsim_backend.app.models import Network, EquipmentLibrary
from src.optinetsim_backend.app.auth import LoginResource, RegisterResource
from src.optinetsim_backend.app.equipment_library import EquipmentLibraryList, EquipmentLibraryDetail


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


def api_init_app(app):
    api = Api(app)
    api.add_resource(LoginResource, '/api/auth/login')
    api.add_resource(RegisterResource, '/api/auth/register')
    api.add_resource(EquipmentLibraryList, '/api/equipment-libraries')
    api.add_resource(EquipmentLibraryDetail, '/api/equipment-libraries/<string:library_id>')

    api.init_app(app)

    return app