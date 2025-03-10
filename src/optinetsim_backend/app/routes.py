from flask_restful import Api

# Project imports
from src.optinetsim_backend.app.auth import *
from src.optinetsim_backend.app.database import *
from src.optinetsim_backend.app.simulation import *


def api_init_app(app):
    api = Api(app)

    # 用户认证相关接口
    api.add_resource(LoginResource, '/api/auth/login')
    api.add_resource(RegisterResource, '/api/auth/register')
    api.add_resource(UserResource, '/api/auth/delete')
    api.add_resource(ChangePasswordResource, '/api/auth/change-password')

    # 网络相关接口
    api.add_resource(NetworkList, '/api/networks')
    api.add_resource(NetworkResource, '/api/networks/<string:network_id>')

    # 拓扑元素相关接口
    api.add_resource(TopologyAddElement, '/api/networks/<string:network_id>/elements')
    api.add_resource(TopologyUpdateElement, '/api/networks/<string:network_id>/elements/<string:element_id>')
    api.add_resource(TopologyDeleteElement, '/api/networks/<string:network_id>/elements/<string:element_id>')

    # 拓扑连接相关接口
    api.add_resource(ConnectionAdd, '/api/networks/<string:network_id>/connections')
    api.add_resource(ConnectionUpdate, '/api/networks/<string:network_id>/connections/<string:connection_id>')
    api.add_resource(ConnectionDelete, '/api/networks/<string:network_id>/connections/<string:connection_id>')

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

    # 全局变量相关接口
    api.add_resource(SimulationConfigResource, '/api/networks/<string:network_id>/simulation-config')
    api.add_resource(SpectrumInformationResource, '/api/networks/<string:network_id>/spectrum-information')
    api.add_resource(SpanParametersResource, '/api/networks/<string:network_id>/span-parameters')

    # 仿真相关接口
    # 添加单链路仿真接口
    api.add_resource(SingleLinkSimulationResource, '/api/simulation/single-link')

    api.init_app(app)

    return app
