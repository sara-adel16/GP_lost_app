from main import app, mysql, routes
from flask import request, make_response, json, jsonify
import MySQLdb.cursors
import firebase_admin
from firebase_admin import credentials, messaging

path = app.root_path + '\FCM\serviceAccountKey.json'

cred = credentials.Certificate(path)
firebase_admin.initialize_app(cred)

def sendPush(title, msg, registration_token, dataObject=None):
    # See documentation on defining a message payload.
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=msg
        ),
        data=dataObject,
        tokens=registration_token,
    )

    # Send a message to the device corresponding to the provided
    # registration token.
    response = messaging.send_multicast(message)
    # Response is a message ID string.
    print('Successfully sent message:', response)


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