from flask import request, jsonify
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from src.optinetsim_backend.app.models import EquipmentLibrary
from bson import ObjectId


class EquipmentLibraryList(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        libraries = EquipmentLibrary.find_by_user_id(user_id)
        libraries_list = [
            {
                "library_id": str(library['_id']),
                "library_name": library['library_name'],
                "created_at": library['created_at'].strftime('%Y-%m-%dT%H:%M:%SZ'),
                "updated_at": library['updated_at'].strftime('%Y-%m-%dT%H:%M:%SZ')
            }
            for library in libraries
        ]
        return libraries_list, 200

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        library_name = request.json.get('library_name')
        library_id = EquipmentLibrary.create(user_id, library_name)
        new_library = EquipmentLibrary.find_by_id(library_id.inserted_id)
        return {
            "library_id": str(new_library['_id']),
            "library_name": new_library['library_name'],
            "created_at": new_library['created_at'].strftime('%Y-%m-%dT%H:%M:%SZ'),
            "updated_at": new_library['updated_at'].strftime('%Y-%m-%dT%H:%M:%SZ')
        }, 201


class EquipmentLibraryDetail(Resource):
    @jwt_required()
    def put(self, library_id):
        library_name = request.json.get('library_name')
        updated_library = EquipmentLibrary.update(library_id, library_name)
        return {
            "library_id": str(updated_library['_id']),
            "library_name": updated_library['library_name'],
            "created_at": updated_library['created_at'].strftime('%Y-%m-%dT%H:%M:%SZ'),
            "updated_at": updated_library['updated_at'].strftime('%Y-%m-%dT%H:%M:%SZ')
        }, 200

    @jwt_required()
    def delete(self, library_id):
        success = EquipmentLibrary.delete(library_id)
        if success:
            return {"message": "Library deleted successfully"}, 200
        else:
            return {"message": "Library not found"}, 404
