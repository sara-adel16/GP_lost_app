from main import mysql
from flask import json, jsonify, make_response

def register_username(username):
    cursor = mysql.connection.cursor()
    user = 'NONE'
    user = cursor.execute(''' SELECT user_id FROM User WHERE the_name = %s ''', (username,))
    cursor.close()

    return True if user else False


def register_phone_number(phone_number):
    cursor = mysql.connection.cursor()
    user = 'NONE'
    user = cursor.execute(''' SELECT user_id FROM User WHERE phone_number = %s ''', (phone_number,))
    cursor.close()

    return True if user else False


def register_email(email):
    cursor = mysql.connection.cursor()
    user = 'NONE'
    user = cursor.execute(''' SELECT user_id FROM User WHERE email = %s ''', (email,))
    cursor.close()

    return True if user else False


def registration(form):
    username = form.get('username')
    phone_number = form.get('phone_number')
    email = form.get('email')

    if register_phone_number(phone_number):
        res = {
            'status': 202,
            'message': 'User already exists. Please Log in.',
            'data': None
        }
        return make_response(jsonify(res)), 202

    if register_username(username):
        res = {
            'status': 409,
            'message': "That username is taken.",
            'data': None
        }
        return make_response(jsonify(res)), 409

    if register_email(email):
        res = {
            'status': 409,
            'message': "That email is taken.",
            'data': None
        }
        return make_response(jsonify(res)), 409

    return None