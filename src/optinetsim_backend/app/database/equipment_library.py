from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId

# Project imports
from src.optinetsim_backend.app.database.models import EquipmentLibraryDB


def validate_edfa_params(params):
    # 定义所有可能的字段及其类型
    valid_fields = {
        "type_variety": str,  # 类型定义
        "type_def": str,  # 类型定义
        "gain_flatmax": (float, int),  # 最大平坦增益
        "gain_min": (float, int),  # 最小增益
        "p_max": (float, int),  # 最大功率
        "nf_min": (float, int),  # 最小噪声系数
        "nf_max": (float, int),  # 最大噪声系数
        "out_voa_auto": bool,  # 是否自动调节输出 VOA
        "allowed_for_design": bool  # 是否允许用于设计
    }

    # 校验字段格式（如果存在）
    for field, field_type in valid_fields.items():
        if field in params and not isinstance(params[field], field_type):
            return False, f"Invalid type for field {field}, expected {field_type}"

    # 校验是否存在未定义的字段
    for field in params:
        if field not in valid_fields:
            return False, f"Undefined field: {field}"

    return True, "Valid Edfa parameters"


def validate_fiber_params(params):
    # 定义所有可能的字段及其类型
    valid_fields = {
        "type_variety": str,  # 类型定义
        "dispersion": (float, int),  # 色散
        "dispersion_slope": (float, int),  # 色散斜率
        "dispersion_per_frequency": dict,  # 频率相关的色散
        "effective_area": (float, int),  # 有效面积
        "gamma": (float, int),  # 非线性系数
        "pmd_coef": (float, int),  # PMD 系数
        "lumped_losses": list,  # 集中损耗
        "raman_coefficient": dict  # 拉曼系数
    }

    # 校验字段格式（如果存在）
    for field, field_type in valid_fields.items():
        if field in params:
            if field == "dispersion_per_frequency":
                # 校验 dispersion_per_frequency 的格式
                if not isinstance(params[field], dict):
                    return False, "dispersion_per_frequency must be a dictionary"
                if "value" not in params[field] or "frequency" not in params[field]:
                    return False, "dispersion_per_frequency must contain 'value' and 'frequency' keys"
                if not isinstance(params[field]["value"], list) or not isinstance(params[field]["frequency"], list):
                    return False, "dispersion_per_frequency 'value' and 'frequency' must be lists"
            elif field == "lumped_losses":
                # 校验 lumped_losses 的格式
                if not isinstance(params[field], list):
                    return False, "lumped_losses must be a list"
                for loss in params[field]:
                    if not isinstance(loss, dict):
                        return False, "Each lumped_loss must be a dictionary"
                    if "position" not in loss or "loss" not in loss:
                        return False, "lumped_loss must contain 'position' and 'loss' keys"
            elif not isinstance(params[field], field_type):
                return False, f"Invalid type for field {field}, expected {field_type}"

    # 校验是否存在未定义的字段
    for field in params:
        if field not in valid_fields:
            return False, f"Undefined field: {field}"

    return True, "Valid Fiber parameters"


def validate_raman_fiber_params(params):
    # 定义 Fiber 的所有字段及其类型
    fiber_fields = {
        "type_variety": str,  # 类型定义
        "dispersion": (float, int),  # 色散
        "dispersion_slope": (float, int),  # 色散斜率
        "dispersion_per_frequency": dict,  # 频率相关的色散
        "effective_area": (float, int),  # 有效面积
        "gamma": (float, int),  # 非线性系数
        "pmd_coef": (float, int),  # PMD 系数
        "lumped_losses": list,  # 集中损耗
        "raman_coefficient": dict  # 拉曼系数
    }

    # 定义 RamanFiber 的额外字段及其类型
    raman_fiber_fields = {
        "raman_pumps": list,  # 拉曼泵浦列表
        "temperature": (float, int),  # 温度
        "loss_coef": dict  # 损耗系数
    }

    # 合并 Fiber 和 RamanFiber 的字段
    valid_fields = {**fiber_fields, **raman_fiber_fields}

    # 校验字段格式（如果存在）
    for field, field_type in valid_fields.items():
        if field in params:
            if field == "dispersion_per_frequency":
                # 校验 dispersion_per_frequency 的格式
                if not isinstance(params[field], dict):
                    return False, "dispersion_per_frequency must be a dictionary"
                if "value" not in params[field] or "frequency" not in params[field]:
                    return False, "dispersion_per_frequency must contain 'value' and 'frequency' keys"
                if not isinstance(params[field]["value"], list) or not isinstance(params[field]["frequency"], list):
                    return False, "dispersion_per_frequency 'value' and 'frequency' must be lists"
            elif field == "lumped_losses":
                # 校验 lumped_losses 的格式
                if not isinstance(params[field], list):
                    return False, "lumped_losses must be a list"
                for loss in params[field]:
                    if not isinstance(loss, dict):
                        return False, "Each lumped_loss must be a dictionary"
                    if "position" not in loss or "loss" not in loss:
                        return False, "lumped_loss must contain 'position' and 'loss' keys"
            elif field == "raman_pumps":
                # 校验 raman_pumps 的格式
                if not isinstance(params[field], list):
                    return False, "raman_pumps must be a list"
                for pump in params[field]:
                    if not isinstance(pump, dict):
                        return False, "Each raman_pump must be a dictionary"
                    if "power" not in pump or "frequency" not in pump or "propagation_direction" not in pump:
                        return False, "raman_pump must contain 'power', 'frequency', and 'propagation_direction' keys"
                    if not isinstance(pump["power"], (float, int)):
                        return False, "raman_pump 'power' must be a number"
                    if not isinstance(pump["frequency"], (float, int)):
                        return False, "raman_pump 'frequency' must be a number"
                    if pump["propagation_direction"] not in ["coprop", "counterprop"]:
                        return False, "raman_pump 'propagation_direction' must be 'coprop' or 'counterprop'"
            elif field == "loss_coef":
                # 校验 loss_coef 的格式
                if not isinstance(params[field], dict):
                    return False, "loss_coef must be a dictionary"
                if "value" not in params[field] or "frequency" not in params[field]:
                    return False, "loss_coef must contain 'value' and 'frequency' keys"
                if not isinstance(params[field]["value"], list) or not isinstance(params[field]["frequency"], list):
                    return False, "loss_coef 'value' and 'frequency' must be lists"
            elif not isinstance(params[field], field_type):
                return False, f"Invalid type for field {field}, expected {field_type}"

    # 校验是否存在未定义的字段
    for field in params:
        if field not in valid_fields:
            return False, f"Undefined field: {field}"

    return True, "Valid RamanFiber parameters"


def validate_roadm_params(params):
    # 定义所有可能的字段及其类型
    valid_fields = {
        "type_variety": str,  # 类型定义
        "target_pch_out_db": (float, int),  # 目标输出功率
        "add_drop_osnr": (float, int),  # 添加/丢弃 OSNR
        "pmd": (float, int),  # PMD
        "pdl": (float, int),  # PDL
        "restrictions": dict  # 限制条件
    }

    # 校验字段格式（如果存在）
    for field, field_type in valid_fields.items():
        if field in params:
            if field == "restrictions":
                # 校验 restrictions 的格式
                if not isinstance(params[field], dict):
                    return False, "restrictions must be a dictionary"
                if "preamp_variety_list" not in params[field] or "booster_variety_list" not in params[field]:
                    return False, "restrictions must contain 'preamp_variety_list' and 'booster_variety_list' keys"
                if not isinstance(params[field]["preamp_variety_list"], list) or not isinstance(params[field]["booster_variety_list"], list):
                    return False, "restrictions 'preamp_variety_list' and 'booster_variety_list' must be lists"
            elif not isinstance(params[field], field_type):
                return False, f"Invalid type for field {field}, expected {field_type}"

    # 校验是否存在未定义的字段
    for field in params:
        if field not in valid_fields:
            return False, f"Undefined field: {field}"

    return True, "Valid Roadm parameters"


def validate_transceiver_params(params):
    # 定义所有可能的字段及其类型
    valid_fields = {
        "type_variety": str,  # 类型定义
        "frequency": dict,  # 频率范围
        "mode": list  # 支持的传输模式
    }

    # 校验 frequency 字段（如果存在）
    if "frequency" in params:
        if not isinstance(params["frequency"], dict):
            return False, "frequency must be a dictionary"
        if "min" not in params["frequency"] or "max" not in params["frequency"]:
            return False, "frequency must contain 'min' and 'max' keys"
        if not isinstance(params["frequency"]["min"], (float, int)) or not isinstance(params["frequency"]["max"],
                                                                                      (float, int)):
            return False, "frequency 'min' and 'max' must be numbers"

    # 校验 mode 字段（如果存在）
    if "mode" in params:
        if not isinstance(params["mode"], list):
            return False, "mode must be a list"

        # 校验每个 mode 的格式
        for mode in params["mode"]:
            if not isinstance(mode, dict):
                return False, "Each mode must be a dictionary"

            # 定义 mode 中可能的字段及其类型
            valid_mode_fields = {
                "type_variety": str,  # 类型定义
                "format": str,  # 格式描述
                "baud_rate": (float, int),  # 波特率
                "OSNR": (float, int),  # 最小 OSNR 要求
                "bit_rate": (float, int),  # 比特率
                "roll_off": (float, int, type(None)),  # 滚降系数，允许为 null
                "tx_osnr": (float, int),  # 发射端 OSNR
                "penalties": list,  # 损伤列表
                "min_spacing": (float, int),  # 最小信道间隔
                "cost": (float, int)  # 成本
            }

            # 校验 mode 中的字段（如果存在）
            for field, field_type in valid_mode_fields.items():
                if field in mode and not isinstance(mode[field], field_type):
                    return False, f"Invalid type for field {field} in mode, expected {field_type}"

            # 校验 penalties 中的每个损伤（如果存在）
            if "penalties" in mode:
                for penalty in mode["penalties"]:
                    if not isinstance(penalty, dict):
                        return False, "Each penalty must be a dictionary"
                    if "chromatic_dispersion" not in penalty and "pmd" not in penalty and "pdl" not in penalty:
                        return False, "Penalty must contain at least one of: chromatic_dispersion, pmd, pdl"
                    if "penalty_value" not in penalty:
                        return False, "Penalty must contain 'penalty_value'"
                    if not isinstance(penalty["penalty_value"], (float, int)):
                        return False, "penalty_value must be a number"

    # 校验是否存在未定义的字段
    for field in params:
        if field not in valid_fields:
            return False, f"Undefined field: {field}"

    return True, "Valid Transceiver parameters"


class EquipmentLibraryList(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        libraries = EquipmentLibraryDB.find_by_user_id(user_id)
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
        library_id = EquipmentLibraryDB.create(user_id, library_name)
        new_library = EquipmentLibraryDB.find_by_id(library_id.inserted_id)
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
        updated_library = EquipmentLibraryDB.update(library_id, library_name)
        return {
            "library_id": str(updated_library['_id']),
            "library_name": updated_library['library_name'],
            "created_at": updated_library['created_at'].strftime('%Y-%m-%dT%H:%M:%SZ'),
            "updated_at": updated_library['updated_at'].strftime('%Y-%m-%dT%H:%M:%SZ')
        }, 200

    @jwt_required()
    def delete(self, library_id):
        success = EquipmentLibraryDB.delete(library_id)
        if success:
            return {"message": "Library deleted successfully"}, 200
        else:
            return {"message": "Library not found"}, 404


class EquipmentList(Resource):
    @jwt_required()
    def get(self, library_id):
        user_id = get_jwt_identity()
        library = EquipmentLibraryDB.find_by_id(library_id)
        if not library or library['user_id'] != ObjectId(user_id):
            return {"message": "Library not found or not authorized"}, 404

        return library['equipments'], 200


class EquipmentAddResource(Resource):
    @jwt_required()
    def post(self, library_id, category):
        user_id = get_jwt_identity()
        library = EquipmentLibraryDB.find_by_id(library_id)
        if not library or library['user_id'] != ObjectId(user_id):
            return {"message": "Library not found or not authorized"}, 404

        equipment = request.json

        # 根据设备类型调用相应的校验函数
        if category == "Edfa":
            is_valid, message = validate_edfa_params(equipment)
        elif category == "Fiber":
            is_valid, message = validate_fiber_params(equipment)
        elif category == "RamanFiber":
            is_valid, message = validate_raman_fiber_params(equipment)
        elif category == "Roadm":
            is_valid, message = validate_roadm_params(equipment)
        elif category == "Transceiver":
            is_valid, message = validate_transceiver_params(equipment)
        else:
            return {"message": "Invalid category"}, 400

        if not is_valid:
            return {"message": message}, 400

        # 调用 add_equipment 方法并传递器件库ID、类别和器件信息
        success = EquipmentLibraryDB.add_equipment(library_id, category, equipment)

        if success:
            # 返回添加成功的器件信息
            return equipment, 201
        else:
            return {"message": "Equipment already exists, can not add this equipment."}, 400


class EquipmentUpdateResource(Resource):
    @jwt_required()
    def put(self, library_id, category, type_variety):
        user_id = get_jwt_identity()
        library = EquipmentLibraryDB.find_by_id(library_id)
        if not library or library['user_id'] != ObjectId(user_id):
            return {"message": "Library not found or not authorized"}, 404

        equipment = request.json

        # 根据设备类型调用相应的校验函数
        if category == "Edfa":
            is_valid, message = validate_edfa_params(equipment)
        elif category == "Fiber":
            is_valid, message = validate_fiber_params(equipment)
        elif category == "RamanFiber":
            is_valid, message = validate_raman_fiber_params(equipment)
        elif category == "Roadm":
            is_valid, message = validate_roadm_params(equipment)
        elif category == "Transceiver":
            is_valid, message = validate_transceiver_params(equipment)
        else:
            return {"message": "Invalid category"}, 400

        if not is_valid:
            return {"message": message}, 400

        # 调用 update_equipment 方法并传递器件库ID、类别、器件类型和新参数
        success = EquipmentLibraryDB.update_equipment(library_id, category, type_variety, equipment)

        if success:
            # 返回更新后的器件信息
            return equipment, 200
        else:
            return {"message": "Equipment not found."}, 404


class EquipmentDeleteResource(Resource):
    @jwt_required()
    def delete(self, library_id, category, type_variety):
        user_id = get_jwt_identity()
        library = EquipmentLibraryDB.find_by_id(library_id)
        if not library or library['user_id'] != ObjectId(user_id):
            return {"message": "Library not found or not authorized"}, 404

        success = EquipmentLibraryDB.delete_equipment(library_id, category, type_variety)
        if success:
            return {"message": "Equipment deleted successfully"}, 200
        else:
            return {"message": "Equipment not found or invalid category"}, 404
