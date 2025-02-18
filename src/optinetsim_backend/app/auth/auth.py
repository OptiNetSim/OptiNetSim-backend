from flask_restful import Resource
from flask import request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from src.optinetsim_backend.app.database.models import UserDB, NetworkDB, EquipmentLibraryDB


class LoginResource(Resource):
    def post(self):
        username = request.json.get('username', None)
        password = request.json.get('password', None)
        user = UserDB.find_by_username(username)
        if user and check_password_hash(user['password'], password):
            access_token = create_access_token(identity=str(user['_id']))
            return {'access_token': access_token}, 200
        return {'msg': 'Bad username or password'}, 401


class RegisterResource(Resource):
    def post(self):
        username = request.json.get('username', None)
        password = request.json.get('password', None)
        email = request.json.get('email', None)
        if UserDB.find_by_username(username):
            return {'msg': 'Username already exists'}, 400
        hashed_password = generate_password_hash(password, method='scrypt')
        UserDB.create(username, hashed_password, email)
        return {'msg': 'User created successfully'}, 201


class UserResource(Resource):
    @jwt_required()
    def delete(self):
        user_id = get_jwt_identity()
        # 删除用户的所有网络
        NetworkDB.delete_by_user_id(user_id)
        # 删除用户的所有设备库
        EquipmentLibraryDB.delete_by_user_id(user_id)
        if UserDB.delete_by_userid(user_id):
            return {'msg': 'User deleted successfully'}, 200
        return {'msg': 'Failed to delete user'}, 400


class ChangePasswordResource(Resource):
    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        old_password = request.json.get('old_password', None)
        new_password = request.json.get('new_password', None)

        if not old_password or not new_password:
            return {'msg': 'old_password and new_password are required'}, 400

        user = UserDB.find_by_userid(user_id)
        if user and check_password_hash(user['password'], old_password):
            hashed_password = generate_password_hash(new_password, method='scrypt')
            UserDB.update_password(user_id, hashed_password)
            return {'msg': 'Password changed successfully'}, 200
        return {'msg': 'Bad old password'}, 401
