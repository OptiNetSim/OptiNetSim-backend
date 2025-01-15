from flask_restful import Api
from flask import Flask
from flask_jwt_extended import JWTManager

# Project imports
from src.optinetsim_backend.app.auth import *
from src.optinetsim_backend.app.database import *
import create_connection
import modify_connection
import delete_connection

app = Flask(__name__)
jwt = JWTManager(app)


def api_init_app(app):
    api = Api(app)

    # 用户认证相关接口
    api.add_resource(LoginResource, '/api/auth/login')
    api.add_resource(RegisterResource, '/api/auth/register')

    # 网络相关接口
    api.add_resource(NetworkList, '/api/networks')
    api.add_resource(NetworkResource, '/api/networks/<string:network_id>')

    # 拓扑元素相关接口
    api.add_resource(TopologyAddElement, '/api/networks/<string:network_id>/elements')
    api.add_resource(TopologyUpdateElement, '/api/networks/<string:network_id>/elements/<string:element_id>')
    api.add_resource(TopologyDeleteElement, '/api/networks/<string:network_id>/elements/<string:element_id>')

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

    # 仿真相关接口
    # TODO: API resource for simulation

    # 连接相关接口
    app.route('/api/networks/<network_id>/connections', methods=['POST'])(create_connection.create_connection)
    app.route('/api/networks/<network_id>/connections/<connection_id>', methods=['PUT'])(modify_connection.update_connection)
    app.route('/api/networks/<network_id>/connections/<connection_id>', methods=['DELETE'])(delete_connection.delete_connection)

    api.init_app(app)

    return app

if __name__ == '__main__':
    jwt_secret_key = input("请输入 JWT 密钥：")
    app.config['JWT_SECRET_KEY'] = jwt_secret_key
    app = api_init_app()
    app.run()