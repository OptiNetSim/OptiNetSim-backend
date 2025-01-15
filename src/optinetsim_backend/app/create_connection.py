from flask import request, jsonify
from flask_jwt_extended import jwt_required


# 存储连接信息的数据库
connections = []


def create_connection(network_id):
    data = request.get_json()
    from_node = data.get('from_node')
    to_node = data.get('to_node')
    # 生成唯一标识
    uid = len(connections)
    new_connection = {
        "uid": uid,
        "from_node": from_node,
        "to_node": to_node
    }
    connections.append(new_connection)
    return jsonify(new_connection), 201