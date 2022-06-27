from flask import Blueprint, request, make_response, json, jsonify
from main import app, mysql, bcrypt, SECRET_KEY, validate, get
import MySQLdb.cursors
import uuid, jwt
from datetime import datetime
import datetime
import face_recognition
from main.FCM import FCMManager as fcm

auth_blueprint = Blueprint('main', __name__)


@app.route('/get-all-posts', methods=['GET'])
def get_all_posts():
    '''
    Get All Posts
    '''
    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * from Post WHERE is_temp = false ''')
    posts = cursor.fetchall()
    cursor.close()

    start = int(request.args.get('start'))
    limit = int(request.args.get('limit'))

    res = {}
    res['posts'] = get.posts(posts, user_id, start, limit, False)
    res['status'] = 200
    return make_response(jsonify(res)), 200


@app.route('/get-saved-posts', methods=['GET'])
def get_saved_posts():
    '''
    Get Saved Posts of the current user
    '''
    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT Post.*, Saved_Posts.* FROM Saved_Posts LEFT JOIN Post
                        ON Saved_Posts.post_id = Post.post_id WHERE Saved_Posts.user_id = %s ''', (user_id,))
    posts = cursor.fetchall()
    cursor.close()

    start = int(request.args.get('start'))
    limit = int(request.args.get('limit'))

    res = {}
    res['posts'] = get.posts(posts, user_id, start, limit, False)
    res['status'] = 200
    return make_response(jsonify(res)), 200


@app.route('/click-post', methods=['GET'])
def click_post():
    '''
    Get all data of a specific post including comments and photos
    '''
    post_id = request.args.get('post_id')
    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * from Post WHERE post_id = %s ''', (post_id,))
    posts = cursor.fetchall()
    cursor.close()

    start, limit = 0, 1

    res = {}
    res['post'] = get.posts(posts, user_id, start, limit, True)
    res['status'] = 200
    return make_response(jsonify(res)), 200


@app.route('/register', methods=['GET', 'POST'])
def register():
    '''
    Registers New User
    :request body: username, phone_number, email, password
    :return: responses with a message telling whether the registration is successful or there is any invalid data
    '''
    data = request.json
    username = data.get('username')
    phone_number = data.get('phone_number')
    email = data.get('email')
    password = data.get('password')

    res = validate.user_data(data)
    if res is not None:
        return make_response(jsonify(res))

    cursor = mysql.connection.cursor()
    cursor.execute(
        ''' INSERT INTO User (the_name, phone_number, the_password, email, fcm_token, user_photo_id)
        VALUES (%s, %s, %s, %s, "", NULL) ''', (username, phone_number, password, email,))

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


@app.route('/login', methods=['GET', 'POST'])
def login():
    '''
    Login users
    :request body: phone_number, password
    :return: responses with a message telling whether the login is successful or there is any invalid data
    '''
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

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT the_name FROM User WHERE phone_number = %s ''', (phone_number,))
    username = cursor.fetchone()
    is_registered = username is not None

    res = {
        'status': 200,
        'message': 'هذا الرقم مسجل بالفعل' if is_registered else 'هذا الرقم غير مسجل',
        'data': {
            'is_registered': is_registered,
            'username': "" if username is None else username['the_name']
        }
    }
    return make_response(jsonify(res)), 200


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    '''
    Updates user password
    :request body: phone number - new password
    :return: message telling that the password is updated successfully
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


@app.route("/search", methods=['POST'])
def search():
    '''
    Face Recognition
    '''
    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)

    data = json.loads(request.form.get('data'))
    is_lost_tmp = data.get('is_lost')
    if type(is_lost_tmp) is bool or type(is_lost_tmp) is int:
        is_lost = is_lost_tmp
    else:
        is_lost = True if is_lost_tmp == "true" else False

    file = request.files.get('main_photo')
    file.save(app.root_path + '\\' + get.path(file.filename))
    unknown_photo = face_recognition.load_image_file(file)
    tmp = face_recognition.face_encodings(unknown_photo)
    if len(tmp) == 0:
        res = {
            "status": 406,
            "message": "من فضلك قم برفع صورة أوضح للوجه"
        }
        return make_response(jsonify(res)), 406

    unknown_face_encoding = tmp[0]

    cursor = mysql.connection.cursor()
    if is_lost:
        cursor.execute(''' SELECT * FROM Found_Person WHERE is_temp = false ''')
    else:
        cursor.execute(''' SELECT * FROM Lost_Person WHERE is_temp = false ''')

    all_people = cursor.fetchall()
    target_posts = []
    for cur_person in all_people:
        post_id = cur_person['post_id']
        cursor.execute(''' SELECT user_id FROM Post WHERE post_id = %s ''', (post_id,))
        data = cursor.fetchone()
        post_user_id = data['user_id']
        if post_user_id == user_id:
            continue

        cursor.execute(''' SELECT photo FROM Post_Photo WHERE post_id = %s ''', (post_id,))
        post_photos = cursor.fetchall()

        known_faces_encoding = []
        for cur_photo in post_photos:
            if cur_photo['photo'] is None:
                continue;
            file = cur_photo['photo'].decode('UTF-8')
            file_name = app.root_path + '\\' + get.path(get.filename(file))
            known_photo = face_recognition.load_image_file(file_name)
            tmp = face_recognition.face_encodings(known_photo)
            if len(tmp) == 0:
                continue
            known_faces_encoding.append(tmp[0])

        # Compare faces
        results = face_recognition.compare_faces(known_faces_encoding, unknown_face_encoding)

        right_target = False
        for cur_photo_res in results:
            right_target |= cur_photo_res

        if right_target:
            cursor.execute(''' SELECT * FROM Post WHERE post_id = %s ''', (post_id,))
            post_data = cursor.fetchone()
            target_posts.append(post_data)

    cursor.close()

    if len(target_posts):
        start = int(request.args.get('start'))
        limit = int(request.args.get('limit'))

        posts = get.posts(target_posts, user_id, start, limit, False)
        res = {
            'posts': posts,
            'status': 200,
            'message': 'تم العثور على بعض النتائج'
        }
    else:
        res = {
            'status': 404,
            'message': 'لم يتم العثور على أي نتائج'
        }

    return make_response(jsonify(res)), 200


@app.route("/create-post", methods=['POST'])
def create_post():
    """
    Creates new post
    :request header: user token
    :request body: name - age - gender - city name - street name - address details
                    - lost or found - more details - photo - extra photos
    :return: user data & lost/found person data
    """
    is_temp_tmp = request.args.get('is_temp')
    data = json.loads(request.form.get('data'))
    clicked_post_id = data.get('clicked_post_id')
    name = data.get('name')
    age = data.get('age')
    gender = data.get('gender')
    city = data.get('city')
    district = data.get('district')
    address_details = data.get('address_details')
    is_lost_tmp = data.get('is_lost')
    if type(is_lost_tmp) is bool or type(is_lost_tmp) is int:
        is_lost = is_lost_tmp
    else:
        is_lost = True if is_lost_tmp == "true" else False
    if type(is_temp_tmp) is bool or type(is_temp_tmp) is int:
        is_temp = is_temp_tmp
    else:
        is_temp = True if is_temp_tmp == "true" else False

    more_details = data.get('more_details')
    main_photo = request.files.get('main_photo')
    extra_photos = request.files.getlist('extra_photos')

    main_photo.save(app.root_path + '\\' + get.path(main_photo.filename))
    if len(extra_photos) and extra_photos[0].filename == "":
        extra_photos = []

    date = datetime.datetime.now()
    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)
    user_data = get.user(user_id)

    cursor = mysql.connection.cursor()
    cursor.execute(''' INSERT INTO Address(city, district, address_details) VALUES (%s, %s, %s) ''',
                   (city, district, address_details,))
    mysql.connection.commit()

    address_id = cursor.lastrowid

    cursor.execute(
        ''' INSERT INTO Post(is_lost, more_details, date_AND_time, address_id, user_id, is_temp) VALUES (%s, %s, %s, %s, %s, %s) ''',
        (is_lost, more_details, date, address_id, user_id, is_temp,))
    mysql.connection.commit()
    post_id = cursor.lastrowid

    cursor.execute(''' INSERT INTO Post_Photo(post_id, photo, is_temp, is_main) VALUES (%s, %s, %s, true) ''', (post_id, main_photo, is_temp,))
    mysql.connection.commit()
    main_photo_id = cursor.lastrowid

    extra_photos_paths = []
    for cur_photo in extra_photos:
        cursor.execute(''' INSERT INTO Post_Photo(post_id, photo, is_temp, is_main) VALUES (%s, %s, %s, false) ''',
                       (post_id, cur_photo, is_temp,))
        mysql.connection.commit()
        extra_photos_paths.append(get.path(cur_photo.filename))
        cur_photo.save(app.root_path + '\\' + get.path(cur_photo.filename))

    if is_lost:
        cursor.execute(''' INSERT INTO Lost_Person(the_name, age, gender, post_id, is_temp) VALUES (%s, %s, %s, %s, %s) ''',
                       (name, age, gender, post_id, is_temp,))
    else:
        cursor.execute(''' INSERT INTO Found_Person(the_name, age, gender, post_id, is_temp) VALUES (%s, %s, %s, %s, %s) ''',
                       (name, age, gender, post_id, is_temp,))
    mysql.connection.commit()

    if is_temp:

        cursor.execute(''' SELECT user_id from post WHERE post_id = %s ''', (clicked_post_id,))
        data = cursor.fetchone()
        clicked_post_user_id = data['user_id']
        cursor.execute(''' SELECT fcm_token from User WHERE user_id = %s ''', (clicked_post_user_id,))
        data = cursor.fetchone()
        fcm_token = data['fcm_token']

        name = user_data['username']
        if is_lost:
            title = 'تم العثور على ذوي أحد الأشخاص الذين أبلغت عن إيجادهم!'
            msg = f'قام {name} بالإبلاغ عن فقدان شخص يشبه أحد الأشخاص الذين قمت بالإبلاغ عن إيجادهم، سيتم التواصل معك'
        else:
            title = 'تم العثور على شخص يشبه أحد الأشخاص الذين أبلغت عن فقدانهم!'
            msg = f'قام {name} بالإبلاغ عن إيجاد شخص يشبه أحد الأشخاص الذين قمت بالإبلاغ عن فقدانهم، سيتم التواصل معك'
        fcm.sendPush(title, msg, [fcm_token], {"post_id": str(post_id)})

        cursor.execute(''' SELECT user_photo_id from User WHERE user_id = %s ''', (user_id,))
        data = cursor.fetchone()
        user_photo_id = data['user_photo_id']

        cursor.execute(
            ''' INSERT INTO Notifications(user_id, user_photo_id, post_photo_id, title, msg) VALUES (%s, %s, %s, %s, %s) ''',
            (clicked_post_user_id, user_photo_id, main_photo_id, title, msg,))
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
                "person_name": name,
                "age": int(age),
                "gender": gender,
                "address": {
                    "city": city,
                    "district": district,
                    "address_details": address_details
                },
                "main_photo": get.path(main_photo.filename),
                "extra_photos": extra_photos_paths
            },
            "is_saved": False,
            "is_owner": True,
            "details": more_details,
            "date": date
        }
    }
    return make_response(jsonify(res)), 200


@app.route("/update-post", methods=['PUT'])
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

    post_id = request.args.get('post_id')
    data = json.loads(request.form.get('data'))

    name = data.get('name')
    age = data.get('age')
    gender = data.get('gender')
    city = data.get('city')
    district = data.get('district')
    address_details = data.get('address_details')
    is_lost_tmp = data.get('is_lost')
    if type(is_lost_tmp) is bool or type(is_lost_tmp) is int:
        is_lost = is_lost_tmp
    else:
        is_lost = True if is_lost_tmp == "true" else False

    more_details = data.get('more_details')

    main_photo = request.files.get('main_photo')
    extra_photos = request.files.getlist('extra_photos')

    main_photo.save(app.root_path + '\\' + get.path(main_photo.filename))
    if len(extra_photos) and extra_photos[0].filename == "":
        extra_photos = []

    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)
    user_data = get.user(user_id)

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT address_id, is_lost, date_AND_time FROM Post WHERE post_id = %s ''', (post_id,))
    data = cursor.fetchone()
    address_id, was_lost, date = data['address_id'], data['is_lost'], data['date_AND_time']

    cursor.execute(
        ''' UPDATE Address SET city = %s, district = %s, address_details = %s WHERE address_id = %s ''',
        (city, district, address_details, address_id,))
    mysql.connection.commit()
    cursor.execute(
        ''' DELETE FROM Post_Photo WHERE post_id = %s ''', (post_id,)
    )
    mysql.connection.commit()
    cursor.execute(''' INSERT INTO Post_Photo(post_id, photo, is_temp, is_main) VALUES (%s, %s, false, true) ''',
                   (post_id, main_photo,))
    mysql.connection.commit()

    extra_photos_paths = []
    for cur_photo in extra_photos:
        cursor.execute(''' INSERT INTO Post_Photo(post_id, photo, is_temp, is_main) VALUES (%s, %s, false, false) ''',
                       (post_id, cur_photo,))
        mysql.connection.commit()
        extra_photos_paths.append(get.path(cur_photo.filename))
        cur_photo.save(app.root_path + '\\' + get.path(cur_photo.filename))

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
        cursor.execute(''' INSERT INTO Lost_Person(the_name, age, gender, post_id, is_temp) VALUES (%s, %s, %s, %s, false) ''',
                       (name, age, gender, post_id,))
    else:
        cursor.execute(''' INSERT INTO Found_Person(the_name, age, gender, post_id, is_temp) VALUES (%s, %s, %s, %s, false) ''',
                       (name, age, gender, post_id,))
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
                "person_name": name,
                "age": int(age),
                "gender": gender,
                "address": {
                    "city": city,
                    "district": district,
                    "address_details": address_details
                },
                "main_photo": get.path(main_photo.filename),
                "extra_photos": extra_photos_paths
            },
            "is_saved": False,
            "is_owner": True,
            "details": more_details,
            "date": date
        }
    }
    return make_response(jsonify(res)), 200


@app.route("/delete-post", methods=['DELETE'])
def delete_post():
    '''
    Deletes a post
    :returns: message telling that the post is successfully deleted
    '''
    post_id = request.args.get('post_id')

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT address_id, is_lost FROM Post WHERE post_id =  %s ''', (post_id,))
    data = cursor.fetchone()
    address_id, is_lost = data['address_id'], data['is_lost']

    cursor.execute(''' DELETE FROM Saved_Posts WHERE post_id = %s ''', (post_id,))
    mysql.connection.commit()
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

@app.route("/save-post", methods=['POST'])
def save_post():
    post_id = request.args.get('post_id')
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

@app.route("/unsave-post", methods=['DELETE'])
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
    '''
    Creates a new comment to a specific post
    :request body: content (text)
    '''
    params = request.args
    post_id = int(params.get('post_id'))
    parent_id = params.get('parent_id')
    content = request.json['content']
    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)
    date = datetime.datetime.now()

    cursor = mysql.connection.cursor()
    cursor.execute(
        ''' INSERT INTO Comment(parent_id, content, date_AND_time, user_id, post_id) VALUES (%s, %s, %s, %s, %s) ''',
        (parent_id, content, date, user_id, post_id,))
    mysql.connection.commit()

    comment_id = cursor.lastrowid
    user_data = get.user(user_id)

    if parent_id == 0 or parent_id == '0':
        title = f'علق {user_data["username"]} على منشورك'
        msg = f'علق {user_data["username"]} على منشورك: {content}'
        cursor.execute(''' SELECT user_id from post WHERE post_id = %s ''', (post_id,))
        data = cursor.fetchone()
        noti_user_id = data['user_id']
    else:
        title = f'قام {user_data["username"]} بالرد على تعليقك'
        msg = f'قام {user_data["username"]} بالرد على تعليقك: {content}'
        cursor.execute(''' SELECT user_id from comment WHERE comment_id = %s ''', (parent_id,))
        data = cursor.fetchone()
        noti_user_id = data['user_id']

    if noti_user_id != user_id:
        cursor.execute(''' SELECT fcm_token from User WHERE user_id = %s ''', (noti_user_id,))
        data = cursor.fetchone()
        fcm_token = data['fcm_token']
        fcm.sendPush(title,msg,[fcm_token],{"post_id": str(post_id)})

        cursor.execute(''' SELECT user_photo_id from User WHERE user_id = %s ''', (user_id,))
        data = cursor.fetchone()
        user_photo_id = data['user_photo_id']

        cursor.execute(''' SELECT post_photo_id from post_photo WHERE post_id = %s and is_main = true ''', (post_id,))
        data = cursor.fetchone()
        main_photo_id = data['post_photo_id']

        cursor.execute(
            ''' INSERT INTO Notifications(user_id, user_photo_id, post_photo_id, title, msg) VALUES (%s, %s, %s, %s, %s) ''',
            (noti_user_id, user_photo_id, main_photo_id, title, msg,))
        mysql.connection.commit()

    cursor.close()
    res = {
        'status': 200,
        'message': 'تم نشر التعليق بنجاح',
        'data': {
            'comment_id': comment_id,
            'content': content,
            'user_id': user_id,
            'post_id': post_id,
            'username': user_data['username'],
            'user_photo': user_data['photo'],
            'date': date
        }
    }
    return make_response(jsonify(res)), 200

@app.route("/update-comment", methods=['PUT'])
def update_comment():
    '''
    Updates a comment
    :request body: content (text)
    '''
    params = request.args
    post_id = int(params.get('post_id'))
    parent_id = params.get('parent_id')
    comment_id = params.get('comment_id')

    content = request.json['content']

    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)

    cursor = mysql.connection.cursor()
    cursor.execute(
        ''' UPDATE Comment SET content = %s WHERE post_id = %s and parent_id = %s and comment_id = %s ''',
        (content, post_id, parent_id, comment_id,))
    mysql.connection.commit()

    cursor.execute(''' SELECT date_AND_time FROM Comment WHERE post_id = %s and parent_id = %s and comment_id = %s ''',
                   (post_id, parent_id, comment_id,))
    data = cursor.fetchone()
    date = data['date_AND_time']
    cursor.close()

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


@app.route("/delete-comment", methods=['DELETE'])
def delete_comment():
    '''
    Deletes a comment
    '''
    params = request.args
    post_id = int(params.get('post_id'))
    parent_id = params.get('parent_id')
    comment_id = params.get('comment_id')

    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)

    cursor = mysql.connection.cursor()
    if parent_id == 0:
        # if it's a main comment, delete it's replies
        cursor.execute(
            ''' DELETE FROM Comment WHERE post_id = %s and parent_id = %s ''', (post_id, comment_id,))
        mysql.connection.commit()

    cursor.execute(
        ''' DELETE FROM Comment WHERE post_id = %s and parent_id = %s and comment_id = %s ''',
        (post_id, parent_id, comment_id,))
    mysql.connection.commit()
    cursor.close()

    res = {
        'status': 200,
        'message': 'تم حذف التعليق بنجاح',
    }
    return make_response(jsonify(res)), 200


@app.route("/profile", methods=['GET'])
def profile():
    '''
    Gets all data of the current user and his/her posts
    '''
    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)

    start = int(request.args.get('start'))
    limit = int(request.args.get('limit'))

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * FROM Post WHERE user_id = %s and is_temp = false ''', (user_id,))
    posts = cursor.fetchall()
    cursor.close()

    tmp_res = get.user(user_id)
    tmp_res['posts'] = get.posts(posts, user_id, start, limit, False)

    res = {
        'status': 200,
        'data': tmp_res
    }
    return make_response(jsonify(res)), 200


@app.route("/update-profile", methods=['PUT'])
def update_profile():
    '''
    Updates data of current user
    '''
    auth_token = request.headers.get('Authorization')
    user_id = decode_auth_token(auth_token)

    data = json.loads(request.form.get('data'))
    username = data.get('username')
    phone_number = data.get('phone_number')
    email = data.get('email')

    profile_photo = request.files.get('profile_photo')

    res = validate.user_data(data)
    if res is not None:
        if res['status'] == 202:
            res['message'] = "هذا الرقم مسجل بالفعل"
        res['status'] = 409
        return make_response(jsonify(res)), 409

    cursor = mysql.connection.cursor()
    if username != "":
        cursor.execute(''' UPDATE User SET the_name = %s WHERE user_id = %s ''', (username, user_id,))
        mysql.connection.commit()

    if phone_number != "":
        cursor.execute(''' UPDATE User SET phone_number = %s WHERE user_id = %s ''', (phone_number, user_id,))
        mysql.connection.commit()

    if email != "":
        cursor.execute(''' UPDATE User SET email = %s WHERE user_id = %s ''', (email, user_id,))
        mysql.connection.commit()

    if profile_photo != "":
        cursor.execute(''' SELECT user_photo_id from User WHERE user_id = %s ''', (user_id,))
        data = cursor.fetchone()
        user_photo_id = data['user_photo_id']
        cursor.execute(''' UPDATE user_photo SET photo = %s WHERE user_photo_id = %s ''',
                       (profile_photo, user_photo_id,))
        mysql.connection.commit()
        profile_photo.save(app.root_path + '\\' + get.path(profile_photo.filename))

    cursor.close()

    res = {
        'status': 200,
        'message': 'تم تحديث ملفك الشخصي بنجاح'
    }
    return make_response(jsonify(res)), 200