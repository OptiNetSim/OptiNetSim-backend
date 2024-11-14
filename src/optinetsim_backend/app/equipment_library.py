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


class EquipmentList(Resource):
    @jwt_required()
    def get(self, library_id):
        user_id = get_jwt_identity()
        library = EquipmentLibrary.find_by_id(library_id)
        if not library or library['user_id'] != ObjectId(user_id):
            return {"message": "Library not found or not authorized"}, 404

        return library['equipments'], 200


class EquipmentAddResource(Resource):
    @jwt_required()
    def post(self, library_id, category):
        user_id = get_jwt_identity()
        library = EquipmentLibrary.find_by_id(library_id)
        if not library or library['user_id'] != ObjectId(user_id):
            return {"message": "Library not found or not authorized"}, 404

        equipment = request.json

        # 调用 add_equipment 方法并传递器件库ID、类别和器件信息
        success = EquipmentLibrary.add_equipment(library_id, category, equipment)

        if success:
            # 返回添加成功的器件信息
            return {
                "type_variety": equipment["type_variety"],
                "params": equipment["params"]
            }, 201
        else:
            return {"message": "Category does not exist or invalid data"}, 400


class EquipmentUpdateResource(Resource):
    @jwt_required()
    def put(self, library_id, category, type_variety):
        user_id = get_jwt_identity()
        library = EquipmentLibrary.find_by_id(library_id)
        if not library or library['user_id'] != ObjectId(user_id):
            return {"message": "Library not found or not authorized"}, 404

        params = request.json.get('params')

        # 调用 update_equipment 方法并传递器件库ID、类别、器件类型和新参数
        success = EquipmentLibrary.update_equipment(library_id, category, type_variety, params)

        if success:
            # 返回更新后的器件信息
            return {
                "type_variety": type_variety,
                "params": params
            }, 200
        else:
            return {"message": "Equipment not found or invalid category"}, 404


class EquipmentDeleteResource(Resource):
    @jwt_required()
    def delete(self, library_id, category, type_variety):
        user_id = get_jwt_identity()
        library = EquipmentLibrary.find_by_id(library_id)
        if not library or library['user_id'] != ObjectId(user_id):
            return {"message": "Library not found or not authorized"}, 404

        success = EquipmentLibrary.delete_equipment(library_id, category, type_variety)
        if success:
            return {"message": "Equipment deleted successfully"}, 200
        else:
            return {"message": "Equipment not found or invalid category"}, 404
