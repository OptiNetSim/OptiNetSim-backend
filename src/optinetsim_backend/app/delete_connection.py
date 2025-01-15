from flask import jsonify
from flask_jwt_extended import jwt_required
from create_connection import app, connections

@app.route('/api/networks/<network_id>/connections/<connection_id>', methods=['DELETE'])
@jwt_required()
def delete_connection(network_id, connection_id):
    try:
        connection_id = int(connection_id)
        if connection_id < 0 or connection_id >= len(connections):
            return jsonify({"message": "Connection not found"}), 404
        deleted_connection = connections.pop(connection_id)
        return jsonify({"message": "Connection deleted successfully", "deleted_connection": deleted_connection}), 200
    except ValueError:
        return jsonify({"message": "Invalid connection ID"}), 400