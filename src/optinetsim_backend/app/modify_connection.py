from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
import create_connection

app = Flask(__name__)
jwt = JWTManager(app)

@app.route('/api/networks/<network_id>/connections/<connection_id>', methods=['PUT'])
@jwt_required()
def update_connection(network_id, connection_id):
    data = request.get_json()
    from_node = data.get('from_node')
    to_node = data.get('to_node')
    for connection in create_connection.connections:
        if connection["uid"] == int(connection_id):
            connection["from_node"] = from_node
            connection["to_node"] = to_node
            return jsonify(connection)
    return jsonify({"message": "Connection not found"}), 404

if __name__ == '__main__':
    jwt_secret_key = input("请输入 JWT 密钥：")
    app.config['JWT_SECRET_KEY'] = jwt_secret_key
    app.run()