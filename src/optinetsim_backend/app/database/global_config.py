from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.exceptions import BadRequest
from bson import ObjectId

# Project imports
from src.optinetsim_backend.app.database.models import NetworkDB


def validate_simulation_config(raman_params, nli_params):
    # 定义 raman_params 和 nli_params 的字段及其类型
    raman_fields = {
        "flag": bool,
        "method": str,
        "order": int,
        "result_spatial_resolution": (int, float),
        "solver_spatial_resolution": (int, float)
    }

    nli_fields = {
        "method": str,
        "dispersion_tolerance": (int, float),
        "phase_shift_tolerance": (int, float),
        "computed_channels": list,
        "computed_number_of_channels": int
    }

    # 检查 raman_params 中是否有额外字段
    for field in raman_params:
        if field not in raman_fields:
            return False, f"Unexpected field '{field}' in raman_params."

    # 检查 nli_params 中是否有额外字段
    for field in nli_params:
        if field not in nli_fields:
            return False, f"Unexpected field '{field}' in nli_params."

    # 校验 raman_params 的字段类型
    for field, expected_type in raman_fields.items():
        if field in raman_params:
            if not isinstance(raman_params[field], expected_type):
                return False, f"Invalid type for raman_params['{field}']. Expected {expected_type}."

    # 校验 nli_params 的字段类型
    for field, expected_type in nli_fields.items():
        if field in nli_params:
            if not isinstance(nli_params[field], expected_type):
                return False, f"Invalid type for nli_params['{field}']. Expected {expected_type}."

    return True, "Validation successful."


def validate_spectrum_information(spectrum_info):
    # 定义 spectrum_info 的字段及其类型
    spectrum_fields = {
        "f_min": (int, float),
        "baud_rate": (int, float),
        "f_max": (int, float),
        "spacing": (int, float),
        "power_dbm": (int, float),
        "power_range_db": list,
        "roll_off": (int, float),
        "tx_osnr": (int, float),
        "sys_margins": (int, float)
    }

    # 检查 spectrum_info 中是否有额外字段
    for field in spectrum_info:
        if field not in spectrum_fields:
            return False, f"Unexpected field '{field}' in spectrum_info."

    # 校验 spectrum_info 的字段类型
    for field, expected_type in spectrum_fields.items():
        if field in spectrum_info:
            if not isinstance(spectrum_info[field], expected_type):
                return False, f"Invalid type for spectrum_info['{field}']. Expected {expected_type}."

    return True, "Validation successful."


def validate_span_parameters(span_parameters):
    # 定义 span_parameters 的字段及其类型
    span_fields = {
        "power_mode": bool,
        "delta_power_range_db": list,
        "max_fiber_lineic_loss_for_raman": (int, float),
        "target_extended_gain": (int, float),
        "max_length": (int, float),
        "length_units": str,
        "max_loss": (int, float),
        "padding": (int, float),
        "EOL": (int, float),
        "con_in": (int, float),
        "con_out": (int, float)
    }

    # 检查 span_parameters 中是否有额外字段
    for field in span_parameters:
        if field not in span_fields:
            return False, f"Unexpected field '{field}' in span_parameters."

    # 校验 span_parameters 的字段类型
    for field, expected_type in span_fields.items():
        if field in span_parameters:
            if not isinstance(span_parameters[field], expected_type):
                return False, f"Invalid type for span_parameters['{field}']. Expected {expected_type}."

    return True, "Validation successful."


class SimulationConfigResource(Resource):
    # 用于更新指定光网络的仿真全局设定
    @jwt_required()  # JWT鉴权
    def put(self, network_id):
        if not ObjectId.is_valid(network_id):
            return {"message": "Invalid network ID format."}, 400

        try:
            # 获取请求体的JSON内容
            data = reqparse.request.get_json()
            raman_params = data['raman_params']
            nli_params = data['nli_params']

            # 校验 raman_params 和 nli_params 的格式
            is_valid, message = validate_simulation_config(raman_params, nli_params)
            if not is_valid:
                return {"message": message}, 400

            # 检查网络是否存在
            user_id = get_jwt_identity()
            network = NetworkDB.find_by_network_id(user_id, network_id)
            if not network:
                return {"message": f"Network {network_id} not found."}, 404

            # 更新数据库中的仿真配置
            simulation_config = {
                "raman_params": raman_params,
                "nli_params": nli_params
            }
            NetworkDB.update_simulation_config(network_id, simulation_config)

            # 返回更新后的仿真配置
            return simulation_config, 200

        except BadRequest as e:
            return {"message": str(e)}, 400
        except Exception as e:
            return {"message": "An error occurred: " + str(e)}, 500


class SpectrumInformationResource(Resource):
    # 更新指定光网络的频谱信息
    @jwt_required()  # JWT鉴权
    def put(self, network_id):
        if not ObjectId.is_valid(network_id):
            return {"message": "Invalid network ID format."}, 400

        try:
            data = reqparse.request.get_json()

            # 校验频谱信息的格式
            spectrum_info = {
                "f_min": data["f_min"],
                "baud_rate": data["baud_rate"],
                "f_max": data["f_max"],
                "spacing": data["spacing"],
                "power_dbm": data["power_dbm"],
                "power_range_db": data["power_range_db"],
                "roll_off": data["roll_off"],
                "tx_osnr": data["tx_osnr"],
                "sys_margins": data["sys_margins"]
            }
            is_valid, message = validate_spectrum_information(spectrum_info)
            if not is_valid:
                return {"message": message}, 400

            # 检查网络是否存在
            user_id = get_jwt_identity()
            network = NetworkDB.find_by_network_id(user_id, network_id)
            if not network:
                return {"message": f"Network {network_id} not found."}, 404

            # 更新数据库中的频谱信息
            NetworkDB.update_spectrum_information(network_id, spectrum_info)

            # 返回更新后的频谱信息
            return spectrum_info, 200

        except BadRequest as e:
            return {"message": str(e)}, 400
        except Exception as e:
            return {"message": "An error occurred: " + str(e)}, 500


class SpanParametersResource(Resource):
    # 更新指定光网络的跨段参数
    @jwt_required()  # JWT鉴权
    def put(self, network_id):
        if not ObjectId.is_valid(network_id):
            return {"message": "Invalid network ID format."}, 400

        try:
            # 获取请求体的 JSON 内容
            data = reqparse.request.get_json()

            # 校验跨段参数的格式
            span_parameters = {
                "power_mode": data["power_mode"],
                "delta_power_range_db": data["delta_power_range_db"],
                "max_fiber_lineic_loss_for_raman": data["max_fiber_lineic_loss_for_raman"],
                "target_extended_gain": data["target_extended_gain"],
                "max_length": data["max_length"],
                "length_units": data["length_units"],
                "max_loss": data["max_loss"],
                "padding": data["padding"],
                "EOL": data["EOL"],
                "con_in": data["con_in"],
                "con_out": data["con_out"]
            }
            is_valid, message = validate_span_parameters(span_parameters)
            if not is_valid:
                return {"message": message}, 400

            # 检查网络是否存在
            user_id = get_jwt_identity()
            network = NetworkDB.find_by_network_id(user_id, network_id)
            if not network:
                return {"message": f"Network {network_id} not found."}, 404

            # 更新数据库中的跨段参数
            NetworkDB.update_span_parameters(network_id, span_parameters)

            # 返回更新后的跨段参数
            return span_parameters, 200

        except BadRequest as e:
            return {"message": str(e)}, 400
        except Exception as e:
            return {"message": "An error occurred: " + str(e)}, 500
