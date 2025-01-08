from flask_restful import Resource
from flask import request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from src.optinetsim_backend.app.database.models import UserDB


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
