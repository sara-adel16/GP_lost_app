from flask import request, make_response, json, jsonify
from main import app, mysql, routes
import MySQLdb.cursors

@app.route('/update-fcm-token', methods=['PUT'])
def update_fcm_token():
    auth_token = request.headers.get('Authorization')
    user_id = routes.decode_auth_token(auth_token)

    fcm_token = request.json.get('fcm_token')

    cursor = mysql.connection.cursor()
    cursor.execute(''' UPDATE User SET fcm_token = %s WHERE user_id = %s ''', fcm_token, user_id)
    mysql.connection.commit()
    cursor.close()

    res = {
        "status": 200,
        "message": "تم التعديل بنجاح"
    }
    return make_response(jsonify(res)), 200
