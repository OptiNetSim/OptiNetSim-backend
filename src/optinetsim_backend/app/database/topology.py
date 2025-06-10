from flask import request, jsonify
from flask_restful import Resource
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
    @staticmethod
    def post(network_id):
        """添加网络拓扑元素"""
        data = request.get_json()

        network = NetworkDB.find_by_network_id(network_id)
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
    @staticmethod
    def put(network_id, element_id):
        """修改网络拓扑元素"""
        data = request.get_json()

        network = NetworkDB.find_by_network_id(network_id)
        if not network:
            return {"message": "Network not found"}, 404

        # 核验输入数据
        element_type = data.get("type")
        if not element_type:
            return {"message": "Element type is required"}, 400

        element_id_inside = data.get("element_id")
        if not element_id_inside:
            pass
        elif element_id_inside != element_id:
            return {"message": "Element id must be the same"}, 400
        else:
            del data["element_id"]

        is_valid, message = validate_element_data(data, element_type)
        if not is_valid:
            return {"message": message}, 400

        # 向 data 中添加 element_id
        data["element_id"] = element_id

        # 重新组织数据，使 element_id 位于首个位置
        data = dict({"element_id": data["element_id"]}, **data)

        res = NetworkDB.update_element(network_id, element_id, data)
        if res.modified_count > 0:
            return data, 200
        elif res.matched_count != 0:
            return {"message": "No changes detected"}, 200
        else:
            return {"message": "Failed to update element"}, 404


class TopologyDeleteElement(Resource):
    @staticmethod
    def delete(network_id, element_id):
        """删除网络拓扑元素"""
        network = NetworkDB.find_by_network_id(network_id)
        if not network:
            return {"message": "Network not found"}, 404

        res = NetworkDB.delete_by_element_id(network_id, element_id)
        if res.modified_count > 0:
            return {"message": "Element deleted successfully"}, 200
        else:
            return {"message": "Element not found"}, 404


# 连接管理实现
def validate_connection_data(network, data):
    """验证连接数据有效性"""
    required_fields = ["from_node", "to_node"]

    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

    # 检查节点是否存在
    from_node_exists = any(str(e["element_id"]) == data["from_node"] for e in network["elements"])
    to_node_exists = any(str(e["element_id"]) == data["to_node"] for e in network["elements"])

    if not from_node_exists:
        return False, "from_node does not exist"
    if not to_node_exists:
        return False, "to_node does not exist"

    return True, "Data is valid"


class ConnectionAdd(Resource):
    @staticmethod
    def post(network_id):
        """创建连接关系"""
        data = request.get_json()

        network = NetworkDB.find_by_network_id(network_id)
        if not network:
            return {"message": "Network not found"}, 404

        # 数据验证
        is_valid, message = validate_connection_data(network, data)
        if not is_valid:
            return {"message": message}, 400

        # 生成唯一连接ID
        connection_id = str(ObjectId())
        connection_data = {
            "connection_id": connection_id,
            "from_node": data["from_node"],
            "to_node": data["to_node"]
        }
        # 添加连接
        update_result = NetworkDB.add_connection(network_id, connection_data)
        if update_result.modified_count == 0:
            return {"message": "Failed to create connection"}, 400

        return connection_data, 201


class ConnectionUpdate(Resource):
    @staticmethod
    def put(network_id, connection_id):
        """更新连接关系"""
        data = request.get_json()

        network = NetworkDB.find_by_network_id(network_id)
        if not network:
            return {"message": "Network not found"}, 404

        # 验证连接存在
        existing_conn = next((c for c in network.get("connections", [])
                              if c["connection_id"] == connection_id), None)
        if not existing_conn:
            return {"message": "Connection not found"}, 404

        # 数据验证
        is_valid, message = validate_connection_data(network, data)
        if not is_valid:
            return {"message": message}, 400

        # 更新连接
        update_data = {
            "from_node": data["from_node"],
            "to_node": data["to_node"]
        }
        update_result = NetworkDB.update_connection(
            network_id, connection_id, update_data
        )

        if update_result.modified_count > 0:
            return update_data, 200
        return {"message": "No changes detected"}, 200


class ConnectionDelete(Resource):
    @staticmethod
    def delete(network_id, connection_id):
        """删除连接关系"""
        network = NetworkDB.find_by_network_id(network_id)
        if not network:
            return {"message": "Network not found"}, 404

        # 删除操作
        delete_result = NetworkDB.delete_connection(network_id, connection_id)
        if delete_result.modified_count > 0:
            return {"message": "Connection deleted successfully"}, 200
        return {"message": "Connection not found"}, 404


# Helper function for service validation
def validate_service_data(network, data, is_update=False):
    """验证业务流量要求数据有效性"""
    required_fields_add = ["source_element_id", "target_element_id", "traffic_requirement"]
    required_fields_traffic = ["bandwidth", "latency"]

    if not is_update:
        # For adding a service
        for field in required_fields_add:
            if field not in data:
                return False, f"Missing required field: {field}"

        # Validate traffic_requirement fields
        if not isinstance(data["traffic_requirement"], dict):
            return False, "traffic_requirement must be an object"
        for field in required_fields_traffic:
            if field not in data["traffic_requirement"]:
                return False, f"Missing required field in traffic_requirement: {field}"

        # Check if source and target elements exist in the network
        source_element_id = str(data["source_element_id"])
        target_element_id = str(data["target_element_id"])

        source_node_exists = any(str(e["element_id"]) == source_element_id for e in network.get("elements", []))
        target_node_exists = any(str(e["element_id"]) == target_element_id for e in network.get("elements", []))

        if not source_node_exists:
            return False, "source_element_id does not exist in network elements"
        if not target_node_exists:
            return False, "target_element_id does not exist in network elements"
    else:  # For updating a service (PUT request)
        if "traffic_requirement" not in data:
            return False, "Missing required field: traffic_requirement"
        if not isinstance(data["traffic_requirement"], dict):
            return False, "traffic_requirement must be an object"
        for field in required_fields_traffic:
            if field not in data["traffic_requirement"]:
                return False, f"Missing required field in traffic_requirement: {field}"

    return True, "Data is valid"


class ServiceAddResource(Resource):
    @staticmethod
    def post(network_id):
        """添加业务流量要求"""
        data = request.get_json()

        network = NetworkDB.find_by_network_id(network_id)
        if not network:
            return {"message": "Network not found"}, 404

        # Validate input data
        is_valid, message = validate_service_data(network, data)
        if not is_valid:
            return {"message": message}, 400

        # Prepare service data for DB insertion
        service_data = {
            "source_element_id": str(data["source_element_id"]),
            "target_element_id": str(data["target_element_id"]),
            "traffic_requirement": data["traffic_requirement"],
            "service_constraints": data.get("service_constraints", {})  # service_constraints is optional
        }

        update_result = NetworkDB.add_service_requirement(network_id, service_data)

        if update_result.modified_count == 0:
            return {"message": "Failed to add service requirement"}, 400

        # Return the newly created service with its generated service_id
        # service_data already contains the service_id generated by NetworkDB method
        return service_data, 201


class ServiceUpdateResource(Resource):
    @staticmethod
    def put(network_id, service_id):
        """修改业务流量要求"""
        data = request.get_json()

        network = NetworkDB.find_by_network_id(network_id)
        if not network:
            return {"message": "Network not found"}, 404

        # Check if service exists
        existing_service = next((s for s in network.get("services", [])
                                 if s["service_id"] == service_id), None)
        if not existing_service:
            return {"message": "Service not found"}, 404

        # Validate input data (only traffic_requirement is expected for update as per API spec)
        is_valid, message = validate_service_data(network, data, is_update=True)
        if not is_valid:
            return {"message": message}, 400

        # Pass only traffic_requirement data to DB method
        traffic_requirement_data = data["traffic_requirement"]

        update_result = NetworkDB.update_service_requirement(
            network_id, service_id, traffic_requirement_data
        )

        if update_result.modified_count > 0:
            # Return the updated service object from the database
            updated_network = NetworkDB.find_by_network_id(network_id)
            if updated_network:
                updated_service = next((s for s in updated_network.get("services", [])
                                        if s["service_id"] == service_id), None)
                if updated_service:
                    return updated_service, 200
            return {"message": "Service updated, but failed to retrieve updated data"}, 200  # Should ideally not happen
        return {"message": "No changes detected or service not found"}, 200


class ServiceDeleteResource(Resource):
    @staticmethod
    def delete(network_id, service_id):
        """删除业务流量要求"""
        network = NetworkDB.find_by_network_id(network_id)
        if not network:
            return {"message": "Network not found"}, 404

        # Check if service exists before attempting deletion
        existing_service = next((s for s in network.get("services", [])
                                 if s["service_id"] == service_id), None)
        if not existing_service:
            return {"message": "Service not found"}, 404

        delete_result = NetworkDB.delete_service_requirement(network_id, service_id)

        if delete_result.modified_count > 0:
            return {"message": "Service deleted successfully"}, 200
        return {"message": "Service not found or already deleted"}, 404
