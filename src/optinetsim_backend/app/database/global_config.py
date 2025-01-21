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

        # 定义请求解析器
        parser = reqparse.RequestParser()
        parser.add_argument('raman_params', type=dict, required=True, help="Raman parameters are required.")
        parser.add_argument('nli_params', type=dict, required=True, help="NLI parameters are required.")

        try:
            # 获取请求体的JSON内容
            args = parser.parse_args()
            raman_params = args['raman_params']
            nli_params = args['nli_params']

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

        # 定义请求参数解析器
        parser = reqparse.RequestParser()
        parser.add_argument('f_min', type=float, required=True, help="Minimum frequency (f_min) is required.")
        parser.add_argument('baud_rate', type=float, required=True, help="Baud rate is required.")
        parser.add_argument('f_max', type=float, required=True, help="Maximum frequency (f_max) is required.")
        parser.add_argument('spacing', type=float, required=True, help="Channel spacing is required.")
        parser.add_argument('power_dbm', type=float, required=True, help="Power (dBm) is required.")
        parser.add_argument('power_range_db', type=list, location='json', required=True,
                            help="Power range is required.")
        parser.add_argument('roll_off', type=float, required=True, help="Roll-off factor is required.")
        parser.add_argument('tx_osnr', type=float, required=True, help="Transmit OSNR is required.")
        parser.add_argument('sys_margins', type=float, required=True, help="System margins are required.")

        try:
            # 解析请求体参数
            args = parser.parse_args()

            # 校验频谱信息的格式
            spectrum_info = {
                "f_min": args["f_min"],
                "baud_rate": args["baud_rate"],
                "f_max": args["f_max"],
                "spacing": args["spacing"],
                "power_dbm": args["power_dbm"],
                "power_range_db": args["power_range_db"],
                "roll_off": args["roll_off"],
                "tx_osnr": args["tx_osnr"],
                "sys_margins": args["sys_margins"]
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

        # 定义请求解析器
        parser = reqparse.RequestParser()
        parser.add_argument('power_mode', type=bool, required=True, help="Power mode is required.")
        parser.add_argument('delta_power_range_db', type=list, location='json', required=True,
                            help="Delta power range is required.")
        parser.add_argument('max_fiber_lineic_loss_for_raman', type=float, required=True,
                            help="Max fiber lineic loss for Raman is required.")
        parser.add_argument('target_extended_gain', type=float, required=True, help="Target extended gain is required.")
        parser.add_argument('max_length', type=float, required=True, help="Max span length is required.")
        parser.add_argument('length_units', type=str, required=True, help="Length units are required.")
        parser.add_argument('max_loss', type=float, required=True, help="Max loss is required.")
        parser.add_argument('padding', type=float, required=True, help="Padding is required.")
        parser.add_argument('EOL', type=float, required=True, help="End of Life (EOL) is required.")
        parser.add_argument('con_in', type=float, required=True, help="Input connection loss is required.")
        parser.add_argument('con_out', type=float, required=True, help="Output connection loss is required.")

        try:
            # 获取请求体的 JSON 内容
            args = parser.parse_args()

            # 校验跨段参数的格式
            span_parameters = {
                "power_mode": args["power_mode"],
                "delta_power_range_db": args["delta_power_range_db"],
                "max_fiber_lineic_loss_for_raman": args["max_fiber_lineic_loss_for_raman"],
                "target_extended_gain": args["target_extended_gain"],
                "max_length": args["max_length"],
                "length_units": args["length_units"],
                "max_loss": args["max_loss"],
                "padding": args["padding"],
                "EOL": args["EOL"],
                "con_in": args["con_in"],
                "con_out": args["con_out"]
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
