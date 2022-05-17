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
@app.route('/get-all-posts', methods=['GET'])
def get_all_posts():
    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * from Post ''')

    start = int(request.args.get('start'))
    limit = int(request.args.get('limit'))
    return get.posts(cursor, user_id, start, limit, False)


@app.route('/get-saved-posts', methods=['GET'])
def get_saved_posts():
    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT Post.*, Saved_Posts.* FROM Saved_Posts LEFT JOIN Post
                        ON Saved_Posts.post_id = Post.post_id WHERE Saved_Posts.user_id = %s ''', (user_id,))

    start = int(request.args.get('start'))
    limit = int(request.args.get('limit'))
    return get.posts(cursor, user_id, start, limit, False)


@app.route('/click-post', methods=['GET'])
def click_post():
    post_id = request.args.get('post_id')
    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * from Post WHERE post_id = %s ''', (post_id,))

    start, limit = 0, 1

    return get.posts(cursor, user_id, start, limit, True)


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

    cursor.execute(''' INSERT INTO Post(is_lost, more_details, date_AND_time, address_id, user_id) VALUES (%s, %s, %s, %s, %s) ''', (is_lost, more_details, date, address_id, user_id,))
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

    cursor.execute(''' INSERT INTO User_Posts(user_id, post_id) VALUES (%s, %s) ''', (user_id, post_id,))
    mysql.connection.commit()

    cursor.close()

    res = {
        "status": 200,
        "message": "تم نشر المنشور بنجاح",
        "data": {
            "post_id": post_id,
            "user_id": user_id,
            "username": user_data['username'],
            "user_photo": user_data['photo'],
            "user_phone_number": user_data['phone_number'],
            "is_lost": is_lost,
            "person_data": {
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
            "more_details": more_details,
            "date": date
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

    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)
    user_data = get.user(user_id)

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT address_id, is_lost, date_AND_time FROM Post WHERE post_id = %s ''', (post_id,))
    data = cursor.fetchone()
    address_id, was_lost, date = data['address_id'], data['is_lost'], data['date_AND_time']

    cursor.execute(
        ''' UPDATE Address SET city = %s, district = %s, address_details = %s WHERE address_id = %s ''', (city, district, address_details, address_id,))
    mysql.connection.commit()

    cursor.execute(
        ''' DELETE FROM Post_Photo WHERE post_id = %s ''', (post_id,)
    )
    mysql.connection.commit()

    cursor.execute(''' INSERT INTO Post_Photo(post_id, photo, is_main) VALUES (%s, %s, true) ''', (post_id, main_photo,))
    mysql.connection.commit()

    for cur_photo in extra_photos:
        cursor.execute(''' INSERT INTO Post_Photo(post_id, photo, is_main) VALUES (%s, %s, false) ''', (post_id, cur_photo,))
        mysql.connection.commit()

    cursor.execute(
        ''' UPDATE Post SET is_lost = %s, more_details = %s WHERE post_id = %s ''', (is_lost, more_details, post_id,))
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
            "user_id": user_id,
            "username": user_data['username'],
            "user_photo": user_data['photo'],
            "user_phone_number": user_data['phone_number'],
            "is_lost": is_lost,
            "person_data": {
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
            "more_details": more_details,
            "date": date
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


@app.route("/create-comment", methods=['POST'])
def create_comment():

    # take data from params: parent_id, post_id
    params = request.args
    post_id = params.get('post_id')
    parent_id = params.get('parent_id')
    # take data from body: content
    content = request.json['content']
    # take token from headers
    auth_token = request.headers.get('Authorization')
    # generate user_id from token
    user_id = decode_auth_token(auth_token)
    # generate date and time
    date = datetime.datetime.now()

    cursor = mysql.connection.cursor()
    cursor.execute(
        ''' INSERT INTO Comment(parent_id, content, date_AND_time, user_id, post_id) VALUES (%s, %s, %s, %s, %s) ''', (parent_id, content, date, user_id, post_id,))
    mysql.connection.commit()
    cursor.close()

    # user data: username, photo
    user_data = get.user(user_id)
    res = {
        'status': 200,
        'message': 'تم نشر التعليق بنجاح',
        'data': {
            'content': content,
            'user_id': user_id,
            'post_id': post_id,
            'username': user_data['username'],
            'user_photo': user_data['photo'],
            'date': date
        }
    }
    return make_response(jsonify(res)), 200

@app.route("/update-comment", methods=['POST'])
def update_comment():

    # take data from params: comment_id, parent_id, post_id
    params = request.args
    post_id = params.get('post_id')
    parent_id = params.get('parent_id')
    comment_id = params.get('comment_id')
    # take data from body: content
    content = request.json['content']
    # take token from headers
    auth_token = request.headers.get('Authorization')
    # generate user_id from token
    user_id = decode_auth_token(auth_token)

    cursor = mysql.connection.cursor()
    cursor.execute(
        ''' UPDATE Comment SET content = %s WHERE post_id = %s and parent_id = %s and comment_id = %s ''', (content, post_id, parent_id, comment_id,))
    mysql.connection.commit()

    cursor.execute(''' SELECT date_AND_time FROM Comment WHERE post_id = %s and parent_id = %s and comment_id = %s ''', (post_id, parent_id, comment_id,))
    data = cursor.fetchone()
    date = data['date_AND_time']
    cursor.close()

    # user data: username, photo
    user_data = get.user(user_id)
    res = {
        'status': 200,
        'message': 'تم تعديل التعليق بنجاح',
        'data': {
            'content': content,
            'user_id': user_id,
            'post_id': post_id,
            'username': user_data['username'],
            'user_photo': user_data['photo'],
            'date': date
        }
    }
    return make_response(jsonify(res)), 200


@app.route("/delete-comment", methods=['POST'])
def delete_comment():
    # take data from params: comment_id, parent_id, post_id
    params = request.args
    post_id = params.get('post_id')
    parent_id = params.get('parent_id')
    comment_id = params.get('comment_id')

    # take token from headers
    auth_token = request.headers.get('Authorization')
    # generate user_id from token
    user_id = decode_auth_token(auth_token)

    cursor = mysql.connection.cursor()

    if parent_id == 0:
        # if it's a main comment, delete it's replies
        cursor.execute(
            ''' DELETE FROM Comment WHERE post_id = %s and parent_id = %s ''', (post_id, comment_id,))
        mysql.connection.commit()

    cursor.execute(
        ''' DELETE FROM Comment WHERE post_id = %s and parent_id = %s and comment_id = %s ''', (post_id, parent_id, comment_id,))
    mysql.connection.commit()
    cursor.close()

    res = {
        'status': 200,
        'message': 'تم حذف التعليق بنجاح',
    }
    return make_response(jsonify(res)), 200