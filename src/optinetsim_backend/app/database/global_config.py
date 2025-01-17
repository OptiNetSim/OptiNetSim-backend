from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required
from werkzeug.exceptions import BadRequest
from pymongo import MongoClient
from bson import ObjectId

# 连接 MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["optinetsim"]  # 数据库名称
networks_collection = db["networks"]  # 集合名称，用于存储网络数据


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

            # 这里可以将数据存入数据库或处理业务逻辑
            # 模拟返回相同的配置数据作为响应
            response = {
                "raman_params": raman_params,
                "nli_params": nli_params
            }

            return response, 200
        except BadRequest as e:
            return {"message": str(e)}, 400
        except Exception as e:
            return {"message": "An error occurred: " + str(e)}, 500


class SpectrumInformationResource(Resource):
    # 更新指定光网络的频谱信息
    @jwt_required()  # JWT鉴权
    def put(self, network_id):
        # 确保 network_id 是有效的 ObjectId 格式
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

            # 检查网络是否存在
            network = networks_collection.find_one({"_id": ObjectId(network_id)})
            if not network:
                return {"message": f"Network {network_id} not found."}, 404

            # 更新网络的频谱信息
            spectrum_information = {
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

            networks_collection.update_one(
                {"_id": ObjectId(network_id)},
                {"$set": {"SI": spectrum_information}}
            )

            # 返回更新后的频谱信息
            return spectrum_information, 200

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

            # 检查网络是否存在
            network = networks_collection.find_one({"_id": ObjectId(network_id)})
            if not network:
                return {"message": f"Network {network_id} not found."}, 404

            # 更新数据库中的跨段参数
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

            networks_collection.update_one(
                {"_id": ObjectId(network_id)},
                {"$set": {"Span": span_parameters}}
            )

            # 返回更新后的跨段参数
            return span_parameters, 200

        except BadRequest as e:
            return {"message": str(e)}, 400
        except Exception as e:
            return {"message": "An error occurred: " + str(e)}, 500
