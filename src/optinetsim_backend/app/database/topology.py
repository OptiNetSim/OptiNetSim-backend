from flask import request, jsonify
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId

# Project imports
from src.optinetsim_backend.app.database.models import NetworkDB, EquipmentLibraryDB


def validate_element_data(data, element_type):
    """核验输入数据是否符合GNPY文档中的字段定义"""
    common_fields = {
        "name": str,  # 元素名称，必须是字符串
        "type": str,  # 元素类型，必须是字符串
        "metadata": dict,  # 元数据，必须是字典
    }

    # 根据元素类型定义不同的字段
    type_specific_fields = {
        "Fiber": {
            "library_id": str,  # 设备库 ID，必须是字符串
            "type_variety": str,  # 可选，必须是字符串
            "params": {
                "length": (int, float),  # 可选，必须是整数或浮点数
                "length_units": str,  # 可选，必须是字符串
                "loss_coef": (int, float, dict),  # 可选，必须是整数、浮点数或字典
                "att_in": (int, float),  # 可选，必须是整数或浮点数
                "con_in": (int, float),  # 可选，必须是整数或浮点数
                "con_out": (int, float),  # 可选，必须是整数或浮点数
            }
        },
        "RamanFiber": {
            "library_id": str,  # 设备库 ID，必须是字符串
            "type_variety": str,  # 可选，必须是字符串
            "operational": {
                "temperature": (int, float),  # 必须是整数或浮点数
                "raman_pumps": list,  # 必须是列表
            },
            "params": {
                "type_variety": str,  # 可选，必须是字符串
                "length": (int, float),  # 可选，必须是整数或浮点数
                "loss_coef": (int, float, dict),  # 可选，必须是整数、浮点数或字典
                "length_units": str,  # 可选，必须是字符串
                "att_in": (int, float),  # 可选，必须是整数或浮点数
                "con_in": (int, float),  # 可选，必须是整数或浮点数
                "con_out": (int, float),  # 可选，必须是整数或浮点数
            }
        },
        "Edfa": {
            "library_id": str,  # 设备库 ID，必须是字符串
            "type_variety": str,  # 可选，必须是字符串
            "operational": {
                "gain_target": (int, float),  # 可选，必须是整数或浮点数
                "delta_p": (int, float),  # 可选，必须是整数或浮点数
                "out_voa": (int, float),  # 可选，必须是整数或浮点数
                "in_voa": (int, float),  # 可选，必须是整数或浮点数
                "tilt_target": (int, float),  # 可选，必须是整数或浮点数
            },
        },
        "Multiband_amplifier": {
            "library_id": str,  # 设备库 ID，必须是字符串
            "type_variety": str,  # 可选，必须是字符串
            "amplifiers": list,  # 必须是列表
        },
        "Roadm": {
            "library_id": str,  # 设备库 ID，必须是字符串
            "type_variety": str,  # 可选，必须是字符串
            "params": {
                "target_pch_out_db": (int, float),  # 可选，必须是整数或浮点数
                "target_psd_out_mWperGHz": (int, float),  # 可选，必须是整数或浮点数
                "target_out_mWperSlotWidth": (int, float),  # 可选，必须是整数或浮点数
                "restrictions": dict,  # 可选，必须是字典
                "per_degree_pch_out_db": dict,  # 可选，必须是字典
                "per_degree_psd_out_mWperGHz": dict,  # 可选，必须是字典
                "per_degree_psd_out_mWperSlotWidth": dict,  # 可选，必须是字典
                "per_degree_impairments": list,  # 可选，必须是列表
                "design_bands": list,  # 可选，必须是列表
                "per_degree_design_bands": dict,  # 可选，必须是字典
            }
        },
        "Fused": {
            "params": {
                "loss": (int, float),  # 可选，必须是整数或浮点数
            }
        },
        "Transceiver": {
            "library_id": str,  # 设备库 ID，必须是字符串
            "type_variety": str,  # 可选，必须是字符串
            # Transceiver 没有额外的字段
        }
    }

    # 检查通用字段
    for field, field_type in common_fields.items():
        if field not in data:
            return False, f"Missing required field: {field}"
        if not isinstance(data[field], field_type):
            return False, f"Field {field} must be of type {field_type}"

    # 检查类型特定的字段
    if element_type in type_specific_fields:
        type_fields = type_specific_fields[element_type]
        for field, field_type in type_fields.items():
            if field in data:
                if isinstance(field_type, dict):
                    # 如果是嵌套字典，递归检查
                    for sub_field, sub_field_type in field_type.items():
                        if sub_field in data[field]:
                            if not isinstance(data[field][sub_field], sub_field_type):
                                return False, f"Field {field}.{sub_field} must be of type {sub_field_type}"
                elif field == "amplifiers" and element_type == "Multiband_amplifier":
                    # 特殊处理 Multiband_amplifier 的 amplifiers 字段
                    if not isinstance(data[field], list):
                        return False, f"Field {field} must be a list"
                    for amplifier in data[field]:
                        if not isinstance(amplifier, dict):
                            return False, f"Each item in {field} must be a dictionary"
                        if "type_variety" not in amplifier:
                            return False, f"Each amplifier in {field} must have a 'type_variety' field"
                        if not isinstance(amplifier["type_variety"], str):
                            return False, f"Field type_variety in {field} must be a string"
                        if "operational" in amplifier:
                            if not isinstance(amplifier["operational"], dict):
                                return False, f"Field operational in {field} must be a dictionary"
                            for op_field, op_type in type_specific_fields["Edfa"]["operational"].items():
                                if op_field in amplifier["operational"]:
                                    if not isinstance(amplifier["operational"][op_field], op_type):
                                        return False, f"Field {op_field} in operational must be of type {op_type}"
                else:
                    if not isinstance(data[field], field_type):
                        return False, f"Field {field} must be of type {field_type}"

    # 检查是否有未定义的字段
    allowed_fields = set(common_fields.keys())
    if element_type in type_specific_fields:
        allowed_fields.update(type_specific_fields[element_type].keys())

    for field in data.keys():
        if field not in allowed_fields:
                return False, f"Undefined field: {field}"

    return True, "Data is valid"


class TopologyAddElement(Resource):
    @jwt_required()
    def post(self, network_id):
        """添加网络拓扑元素"""
        user_id = get_jwt_identity()
        data = request.get_json()

        network = NetworkDB.find_by_network_id(user_id, network_id)
        if not network:
            return {"message": "Network not found"}, 404

        # 核验输入数据
        element_type = data.get("type")
        if not element_type:
            return {"message": "Element type is required"}, 400

        is_valid, message = validate_element_data(data, element_type)
        if not is_valid:
            return {"message": message}, 400

        # 生成 element_id
        data["element_id"] = str(ObjectId())

        # 重新组织数据，使 element_id 位于首个位置
        data = dict({"element_id": data["element_id"]}, **data)

        res = NetworkDB.add_element(network_id, data)
        if res.modified_count > 0:
            return data, 201
        else:
            return {"message": "Failed to add element"}, 400


class TopologyUpdateElement(Resource):
    @jwt_required()
    def put(self, network_id, element_id):
        """修改网络拓扑元素"""
        user_id = get_jwt_identity()
        data = request.get_json()

        # 向 data 中添加 uid
        data["element_id"] = element_id

        # 重新组织数据，使 element_id 位于首个位置
        data = dict({"element_id": data["element_id"]}, **data)

        network = NetworkDB.find_by_network_id(user_id, network_id)
        if not network:
            return {"message": "Network not found"}, 404

        # 核验输入数据
        element_type = data.get("type")
        if not element_type:
            return {"message": "Element type is required"}, 400

        is_valid, message = validate_element_data(data, element_type)
        if not is_valid:
            return {"message": message}, 400

        res = NetworkDB.update_element(network_id, element_id, data)
        if res.modified_count > 0:
            return data, 200
        elif res.matched_count != 0:
            return {"message": "No changes detected"}, 200
        else:
            return {"message": "Failed to update element"}, 404


class TopologyDeleteElement(Resource):
    @jwt_required()
    def delete(self, network_id, element_id):
        """删除网络拓扑元素"""
        user_id = get_jwt_identity()

        network = NetworkDB.find_by_network_id(user_id, network_id)
        if not network:
            return {"message": "Network not found"}, 404

        res = NetworkDB.delete_by_element_id(network_id, element_id)
        if res.modified_count > 0:
            return {"message": "Element deleted successfully"}, 200
        else:
            return {"message": "Element not found"}, 404
