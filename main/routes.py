from flask import Blueprint, request, make_response, json, jsonify
#from flask_jwt import JWT
from main import app, mysql, bcrypt, SECRET_KEY, validate, get
import MySQLdb.cursors
import uuid, jwt
from datetime import datetime
import datetime

auth_blueprint = Blueprint('main', __name__)

'''
Get All Posts
'''
@app.route('/home', methods=['GET'])
def home():
    auth_token = request.headers.get('Authorization')
    cur_user_id = decode_auth_token(auth_token)

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * from Post ''')

    all_posts = []
    cur_post = cursor.fetchone()
    while cur_post:
        # processing one post
        cur_post_data = {}

        user = get.user(cur_post['user_id'])

        reported_person_data = get.lost_person(cur_post['post_id']) if cur_post['is_lost'] else get.found_person(cur_post['post_id'])
        reported_person_data['address'] = get.address(cur_post['address_id'])
        reported_person_data['main_photo'], reported_person_data['extra_photos'] = get.post_photos(cur_post['post_id'])

        cur = mysql.connection.cursor()
        cur.execute(''' SELECT * from Saved_Posts WHERE user_id = %s and post_id = %s ''', (cur_user_id, cur_post['post_id'],))
        is_saved = cur.fetchone()
        cur.close()

        cur_post_data = {
            'post_id': cur_post['post_id'],
            'user_id': user['user_id'],
            'username': user['username'],
            'user_photo': user['photo'],
            'is_lost': cur_post['is_lost'] == 1,
            'lost_person_data' if cur_post['is_lost'] else 'found_person_data': reported_person_data,
            'details': cur_post['more_details'],
            'is_owner': cur_user_id == cur_post['user_id'],
            'is_saved': is_saved is not None,
            'Comments': get.post_comments(cur_post['post_id'])
        }

        all_posts.append(cur_post_data)
        cur_post = cursor.fetchone()

    cursor.close()

    start, limit = int(request.args['start']), int(request.args['limit'])

    return make_response(jsonify({
        'Posts': all_posts[start: start + limit],
        'status': 200
    })), 200

'''
Register New User
'''
@app.route('/register', methods=['GET', 'POST'])
def register():
    data = request.json
    username = data.get('username')
    phone_number = data.get('phone_number')
    email = data.get('email') if data.get('email') is not None else ""
    password = data.get('password')

    res = validate.registration(data)
    if res is not None:
        return res

    cursor = mysql.connection.cursor()
    cursor.execute(
        ''' INSERT INTO User (the_name, phone_number, the_password, email, user_photo_id) VALUES (%s, %s, %s, %s, NULL) ''', (username, phone_number, password, email,))

    user_id = cursor.lastrowid

    mysql.connection.commit()
    cursor.close()

    res = {
        'status': 200,
        'message': "تم التسجيل بنجاح",
        'data': {
            'id': user_id,
            'username': username,
            'phone_number': phone_number,
            'email': email
        }
    }
    return make_response(jsonify(res)), 200


'''
Login
'''
@app.route('/login', methods=['GET', 'POST'])
def login():
    data = request.json
    phone_number, password = data.get('phone_number'), data.get('password')

    cursor = mysql.connection.cursor()
    user = 'NONE'
    cursor.execute(''' SELECT * FROM User WHERE phone_number = %s ''', (phone_number,))
    user = cursor.fetchone()
    cursor.close()

    if user and user['the_password'] == password:

        token = encode_auth_token(user['user_id'])
        res = {
            'status': 200,
            'message': "تم تسجيل الدخول بنجاح",
            'data': {
                'id': user['user_id'],
                'username': user['the_name'],
                'phone_number': user['phone_number'],
                'email': user['email'],
                'token': token.decode(),
            }
        }
        return make_response(jsonify(res)), 200

    else:
        res = {
            'status': 404,
            'message': "فشل تسجيل الدخول، تأكد من رقم الهاتف وكلمة السر",
            'data': None
        }
        return make_response(jsonify(res)), 404


def encode_auth_token(user_id):
    """
    Generates the Auth Token
    :return: string
    """
    payload = {
        'iat': datetime.datetime.utcnow(),
        'sub': user_id
    }
    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm='HS256'
    )


def decode_auth_token(auth_token):
    """
    Decodes the auth token
    :param auth_token:
    :return: integer [user_id]
    """
    payload = jwt.decode(auth_token, SECRET_KEY)
    return payload['sub']


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    '''
    Checks if phone number exists
    :request body: phone number
    :return: bool
    '''
    data = request.json
    phone_number = data.get('phone_number')
    is_registered = validate.register_phone_number(phone_number)

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT the_name FROM User WHERE phone_number = %s ''', (phone_number,))
    username = cursor.fetchone()
    res = {
        'status': 200,
        'Is Registered?': is_registered,
        'username': "" if username is None else username['the_name']
    }
    return make_response(jsonify(res)), 200


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    '''
    Updates user password with the new one
    :request body: phone number - new password
    '''
    data = request.json
    phone_number = data.get('phone_number')
    password = data.get('password')

    cursor = mysql.connection.cursor()
    cursor.execute(''' UPDATE User SET the_password = %s WHERE phone_number = %s ''', (password, phone_number,))
    mysql.connection.commit()
    cursor.close()
    res = {
        'status': 200,
        'message': "تم تحديث كلمة السر",
    }
    return make_response(jsonify(res)), 200


@app.route("/create-post", methods=['GET', 'POST'])
def create_post():
    """
    Creates new post
    :request header: user token
    :request body: name - age - gender -
                    city name - street name - address details -
                    lost or found - more details - photo - extra photos
    :return: user data & lost/found person data
    """

    data = request.json

    name = data.get('name')
    age = data.get('age')
    gender = data.get('gender')
    city = data.get('city')
    district = data.get('district')
    address_details = data.get('address_details')
    is_lost = data.get('is_lost')
    more_details = data.get('more_details')
    main_photo = data.get('photo')

    extra_photos = data.get('extra_photos')
    if extra_photos is None:
        extra_photos = []

    date = datetime.datetime.now()
    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)
    user_data = get.user(user_id)

    cursor = mysql.connection.cursor()
    cursor.execute(''' INSERT INTO Address(city, district, address_details) VALUES (%s, %s, %s) ''', (city, district, address_details,))
    mysql.connection.commit()

    address_id = cursor.lastrowid

    cursor.execute(''' INSERT INTO Post(is_lost, more_details, date_AND_time, address_id, user_id) VALUES (%s, %s, %s, %s, %s) ''', (is_lost, more_details, date, address_id, user_data['user_id'],))
    mysql.connection.commit()

    post_id = cursor.lastrowid

    cursor.execute(''' INSERT INTO Post_Photo(post_id, photo, is_main) VALUES (%s, %s, true) ''', (post_id, main_photo))
    mysql.connection.commit()

    for cur_photo in extra_photos:
        cursor.execute(''' INSERT INTO Post_Photo(post_id, photo, is_main) VALUES (%s, %s, false) ''', (post_id, cur_photo))
        mysql.connection.commit()

    if is_lost:
        cursor.execute(''' INSERT INTO Lost_Person(the_name, age, gender, post_id) VALUES (%s, %s, %s, %s) ''', (name, age, gender, post_id,))
    else:
        cursor.execute(''' INSERT INTO Found_Person(the_name, age, gender, post_id) VALUES (%s, %s, %s, %s) ''', (name, age, gender, post_id,))

    mysql.connection.commit()
    cursor.close()

    res = {
        "status": 200,
        "message": "تم نشر المنشور بنجاح",
        "data": {
            "post_id": post_id,
            "user_id": user_data['user_id'],
            "username": user_data['username'],
            "user_photo": user_data['photo'],
            "user_phone_number": user_data['phone_number'],
            "is_lost": is_lost,
            "lost_person_data" if is_lost else "found_person_data": {
                "name": name,
                "age": age,
                "gender": gender,
                "address": {
                    "city": city,
                    "district": district,
                    "address_details": address_details
                },
                "main_photo": main_photo,
                "extra_photos": extra_photos
            },
            "more_details": more_details
        }
    }
    return make_response(jsonify(res)), 200


@app.route("/update-post", methods=['GET', 'POST'])
def update_post():
    """
        Updates a post
        :params: post_id
        :request header: user token
        :request body: name - age - gender -
                        city name - street name - address details -
                        lost or found - more details - photo - extra photos
        :return: user data & lost/found person data
    """

    post_id = request.args['post_id']
    data = request.json

    name = data.get('name')
    age = data.get('age')
    gender = data.get('gender')
    city = data.get('city')
    district = data.get('district')
    address_details = data.get('address_details')
    is_lost = data.get('is_lost')
    more_details = data.get('more_details')
    main_photo = data.get('photo')

    extra_photos = data.get('extra_photos')
    if extra_photos is None:
        extra_photos = []

    date = datetime.datetime.now()
    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)
    user_data = get.user(user_id)
    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT address_id, is_lost FROM Post WHERE post_id = %s ''', (post_id,))
    tmp = cursor.fetchone()
    address_id, was_lost = tmp['address_id'], tmp['is_lost']
    cursor.execute(
        ''' UPDATE Address SET city = %s, district = %s, address_details = %s WHERE address_id = %s ''', (city, district, address_details, address_id,))
    mysql.connection.commit()

    cursor.execute(
        ''' DELETE FROM Post_Photo WHERE post_id = %s ''', (post_id,)
    )

    cursor.execute(''' INSERT INTO Post_Photo(post_id, photo, is_main) VALUES (%s, %s, true) ''', (post_id, main_photo,))
    mysql.connection.commit()

    for cur_photo in extra_photos:
        cursor.execute(''' INSERT INTO Post_Photo(post_id, photo, is_main) VALUES (%s, %s, false) ''', (post_id, cur_photo,))
        mysql.connection.commit()

    cursor.execute(
        ''' UPDATE Post SET is_lost = %s, more_details = %s, date_AND_time = %s WHERE post_id = %s ''', (is_lost, more_details, date, post_id,))
    mysql.connection.commit()

    if was_lost:
        cursor.execute(
            ''' DELETE FROM Lost_Person WHERE post_id = %s ''', (post_id,)
        )
    else:
        cursor.execute(
            ''' DELETE FROM Found_Person WHERE post_id = %s ''', (post_id,)
        )

    mysql.connection.commit()
    if is_lost:
        cursor.execute(''' INSERT INTO Lost_Person(the_name, age, gender, post_id) VALUES (%s, %s, %s, %s) ''', (name, age, gender, post_id,))
    else:
        cursor.execute(''' INSERT INTO Found_Person(the_name, age, gender, post_id) VALUES (%s, %s, %s, %s) ''', (name, age, gender, post_id,))
    mysql.connection.commit()
    cursor.close()

    res = {
        "status": 200,
        "message": "تم تحديث المنشور بنجاح",
        "data": {
            "user_id": user_data['user_id'],
            "username": user_data['username'],
            "user_photo": user_data['photo'],
            "user_phone_number": user_data['phone_number'],
            "is_lost": is_lost,
            "lost_person_data" if is_lost else "found_person_data": {
                "name": name,
                "age": age,
                "gender": gender,
                "address": {
                    "city": city,
                    "district": district,
                    "address_details": address_details
                },
                "main_photo": main_photo,
                "extra_photos": extra_photos
            },
            "more_details": more_details
        }
    }
    return make_response(jsonify(res)), 200


@app.route("/delete-post", methods=['GET', 'POST'])
def delete_post():
    '''
    Deletes a post
    '''
    post_id = request.args['post_id']

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT address_id, is_lost FROM Post WHERE post_id =  %s ''', (post_id,))
    data = cursor.fetchone()
    address_id, is_lost = data['address_id'], data['is_lost']

    if is_lost:
        cursor.execute(''' DELETE FROM Lost_Person WHERE post_id = %s ''', (post_id,))
    else:
        cursor.execute(''' DELETE FROM Found_Person WHERE post_id = %s ''', (post_id,))
    mysql.connection.commit()
    cursor.execute(''' DELETE FROM Post_Photo WHERE post_id = %s ''', (post_id,))
    mysql.connection.commit()
    cursor.execute(''' DELETE FROM Post WHERE post_id = %s ''', (post_id,))
    mysql.connection.commit()
    cursor.execute(''' DELETE FROM Address WHERE address_id = %s ''', (address_id,))
    mysql.connection.commit()

    cursor.close()

    res = {
        "message": "تم حذف المنشور بنجاح",
        "status": 200
    }
    return make_response(jsonify(res)), 200

@app.route("/save-post", methods=['GET', 'POST'])
def save_post():
    post_id = request.args['post_id']
    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)

    cursor = mysql.connection.cursor()
    cursor.execute(''' INSERT INTO Saved_Posts(user_id, post_id) VALUES (%s, %s) ''', (user_id, post_id,))
    mysql.connection.commit()
    cursor.close()

    res = {
        "message": "تم إضافة المنشور إلى منشوراتك المحفوظة",
        "status": 200
    }
    return make_response(jsonify(res)), 200

@app.route("/unsave-post", methods=['GET', 'POST'])
def unsave_post():
    post_id = request.args['post_id']
    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)

    cursor = mysql.connection.cursor()
    cursor.execute(''' DELETE FROM Saved_Posts WHERE user_id = %s and post_id = %s ''', (user_id, post_id,))
    mysql.connection.commit()
    cursor.close()

    res = {
        "message": "تم إزالة المنشور من منشوراتك المحفوظة",
        "status": 200
    }
    return make_response(jsonify(res)), 200