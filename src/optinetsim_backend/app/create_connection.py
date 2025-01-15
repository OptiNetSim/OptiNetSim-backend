from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity

app = Flask(__name__)
jwt = JWTManager(app)

# 存储连接信息的数据库
connections = []

@app.route('/api/networks/<network_id>/connections', methods=['POST'])
@jwt_required()
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

if __name__ == '__main__':
    jwt_secret_key = input("请输入 JWT 密钥：")
    app.config['JWT_SECRET_KEY'] = jwt_secret_key
    app.run()