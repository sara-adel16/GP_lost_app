from flask import Blueprint, request, make_response, json, jsonify
from flask_jwt import JWT
from main import app, mysql, bcrypt, SECRET_KEY, validate
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
    pass
    # cursor = mysql.connection.cursor()
    # cursor.execute('''SELECT Comment.*, User.*
    #                          FROM Comment
    #                          LEFT JOIN User
    #                          ON Comment.user_id = User.user_id
    #                          ORDER BY parent_id ASC''')
    # mp = {}
    # row = cursor.fetchone()
    # while row:
    #     comment_user = row['user_id'];
    #     comment_id = row['comment_id'];
    #     content = row['content'];
    #     parent_id = row['parent_id'];
    #
    #     print(comment_user, comment_id, content, parent_id)
    #     if parent_id != 0:
    #         if parent_id not in mp:
    #             mp[parent_id] = []
    #         mp[parent_id].append([comment_id, content])
    #     row = cursor.fetchone()
    #
    # res = []
    # lst = mp.keys()
    # for key in lst:
    #     sublst = mp[key]
    #
    #     tmp2 = []
    #     for item in sublst:
    #         tmp2.append({
    #             'Id': item[0],
    #             'Content': item[1]
    #         })
    #
    #     cursor.execute('''SELECT content FROM Comment WHERE comment_id = 60''')
    #     content = cursor.fetchone()
    #     tmp = {
    #         'Id': key,
    #         'Content': content['content'],
    #         'replies': tmp2
    #     }
    #     res.append(tmp)
    #
    # return jsonify({"Comments": res})

    # data = request.args
    # start, limit = data.get('start', 'limit')
    #
    # cursor = mysql.connection.cursor()
    # lst = cursor.execute(''' SELECT * FROM Post LIMIT %s, %s''', (start, limit))
    # cursor.close()
    #
    # res = {
    #     "posts", lst
    # }
    # return make_response(jsonify(res)), 200



'''
Register New User
'''
@app.route('/register', methods=['GET', 'POST'])
def register():
    data = request.json
    username = data.get('username')
    phone_number = data.get('phone_number')
    email = data.get('email')
    password = data.get('password')

    res = validate.registration(data)
    if res is not None:
        return res

    #store the new user's data in the database
    cursor = mysql.connection.cursor()
    cursor.execute(
       # cursor.execute('INSERT INTO accounts VALUES (NULL, % s, % s, % s)', (username, password, email,))
        ''' INSERT INTO User (the_name, phone_number, the_password, email, user_photo_id) VALUES (%s, %s, %s, %s, NULL) ''', (username, phone_number, password, email,))

    cursor.execute(''' SELECT * FROM User WHERE phone_number = %s ''', (phone_number,))
    user = cursor.fetchone()

    mysql.connection.commit()
    cursor.close()

    res = {
        'status': 200,
        'message': "Successfully registered.",
        'data': {
            'id': user['user_id'],
            'username': user['the_name'],
            'phone_number': user['phone_number'],
            'email': user['email']
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
            'message': "Logged in successfully",
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
            'message': "Login Unsuccessful, User does not exist or password is not correct",
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


def get_user(auth_token):
    user_id = decode_auth_token(auth_token)

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * FROM User WHERE user_id = %s''', (user_id,))
    user = cursor.fetchone()

    user_photo_id = user['user_photo_id']
    cursor.execute(''' SELECT photo FROM User_Photo WHERE user_photo_id = %s''', (user_photo_id,))
    photo = cursor.fetchone()

    res = {
        'user_id': user['user_id'],
        'phone_number': user['phone_number'],
        'username': user['the_name'],
        'photo': photo
    }
    return res



@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    '''
    Checks if phone number exists
    :request body: phone number
    :return: bool
    '''
    data = request.json
    phone_number = data.get('phone_number')
    res = {
        "Is Registered?": validate.register_phone_number(phone_number)
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
        'message': "Password has been updated",
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
    date = datetime.datetime.now()
    auth_header = request.headers.get('Authorization')
    user_data = get_user(auth_header)

    cursor = mysql.connection.cursor()
    cursor.execute(''' INSERT INTO Address(city, district, address_details) VALUES (%s, %s, %s) ''', (city, district, address_details,))
    mysql.connection.commit()

    address_id = cursor.lastrowid

    cursor.execute(''' INSERT INTO Post(is_lost, more_details, date_AND_time, address_id, user_id) VALUES (%s, %s, %s, %s, %s) ''', (is_lost, more_details, date, address_id, user_data['user_id'],))
    mysql.connection.commit()

    post_id = cursor.lastrowid

    cursor.execute(''' INSERT INTO Post_Photo(post_id, photo) VALUES (%s, %s) ''', (post_id, user_data['photo']))
    mysql.connection.commit()

    if is_lost:
        cursor.execute(''' INSERT INTO Lost_Person(the_name, age, gender, post_id) VALUES (%s, %s, %s, %s) ''', (name, age, gender, post_id,))
    else:
        cursor.execute(''' INSERT INTO Found_Person(the_name, age, gender, post_id) VALUES (%s, %s, %s, %s) ''', (name, age, gender, post_id,))

    mysql.connection.commit()
    cursor.close()

    res = {
        "status": 200,
        "message": "post is created successfully",
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


@app.route("/update-post", methods=['GET', 'POST'])
def update_post():
    """
        Deletes a post
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
    date = datetime.datetime.now()
    auth_header = request.headers.get('Authorization')
    user_data = get_user(auth_header)

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT address_id,is_lost FROM Post WHERE post_id = %s ''', (post_id,))
    tmp = cursor.fetchone()
    address_id, was_lost = tmp['address_id'], tmp['is_lost']
    cursor.execute(
        ''' UPDATE Address SET city = %s, district = %s, address_details = %s WHERE address_id = %s ''', (city, district, address_details, address_id,))
    mysql.connection.commit()
    cursor.execute(
        ''' UPDATE post_photo SET photo = %s WHERE post_id = %s ''', (user_data['photo'], post_id,))
    mysql.connection.commit()
    cursor.execute(
        ''' UPDATE Post SET is_lost = %s, more_details = %s, date_AND_time = %s WHERE post_id = %s ''', (is_lost, more_details, date, post_id,))
    mysql.connection.commit()

    if was_lost:
        cursor.execute(
            ''' DELETE FROM Lost_Person WHERE post_id = %s ''', (post_id)
        )
    else:
        cursor.execute(
            ''' DELETE FROM Found_Person WHERE post_id = %s ''', (post_id)
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
        "message": "post is updated successfully",
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
    post_id = request.args['post_id']

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT address_id FROM Post WHERE post_id =  %s ''', (post_id,))
    address_id = cursor.fetchone()

    cursor.execute(''' DELETE FROM Lost_Person WHERE post_id = %s ''', (post_id,))
    mysql.connection.commit()
    cursor.execute(''' DELETE FROM Post_Photo WHERE post_id = %s ''', (post_id,))
    mysql.connection.commit()
    cursor.execute(''' DELETE FROM Post WHERE post_id = %s ''', (post_id,))
    mysql.connection.commit()
    cursor.execute(''' DELETE FROM Address WHERE address_id = %s ''', (address_id,))
    mysql.connection.commit()

    cursor.close()


