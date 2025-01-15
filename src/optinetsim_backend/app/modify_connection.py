from flask import request, jsonify
from flask_jwt_extended import jwt_required


def update_connection(network_id, connection_id):
    data = request.get_json()
    from_node = data.get('from_node')
    to_node = data.get('to_node')
    for connection in connections:
        if connection["uid"] == int(connection_id):
            connection["from_node"] = from_node
            connection["to_node": to_node]
            return jsonify(connection)
    return jsonify({"message": "Connection not found"}), 404