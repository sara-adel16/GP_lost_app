from main import mysql
from flask import json, jsonify, make_response

def validate_phone_number(phone_number):
    cursor = mysql.connection.cursor()
    user = 'NONE'
    user = cursor.execute(''' SELECT user_id FROM User WHERE phone_number = %s ''', (phone_number,))
    cursor.close()

    return True if user else False


def validate_email(email):
    cursor = mysql.connection.cursor()
    user = 'NONE'
    user = cursor.execute(''' SELECT user_id FROM User WHERE email = %s ''', (email,))
    cursor.close()

    return True if user else False


def user_data(form):
    phone_number = form.get('phone_number')
    email = form.get('email')

    if phone_number is not None and phone_number != "" and validate_phone_number(phone_number):
        res = {
            'status': 202,
            'message': 'هذا المستخدم موجود بالفعل، قم بتسجيل الدخول',
            'data': None
        }
        return res

    if email is not None and email != "" and validate_email(email):
        res = {
            'status': 409,
            'message': "هذا البريد الإلكتروني مُستخدم",
            'data': None
        }
        return res

    return None