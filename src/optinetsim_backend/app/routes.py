from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from src.optinetsim_backend.app.models import Network
from src.optinetsim_backend.app.auth import LoginResource, RegisterResource


class NetworkList(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        networks = Network.find_by_user_id(user_id)
        # Convert ObjectId to string and datetime to string, filter out only the required fields
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
    api.add_resource(NetworkList, '/api/networks')
    api.add_resource(LoginResource, '/api/auth/login')
    api.add_resource(RegisterResource, '/api/auth/register')

    api.init_app(app)

    return app
