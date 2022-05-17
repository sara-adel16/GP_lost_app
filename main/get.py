from main import mysql
from flask import json, jsonify, make_response


def user(user_id):

    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * FROM User WHERE user_id = %s''', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    photo = user_photo(user['user_photo_id'])

    res = {
        'phone_number': user['phone_number'],
        'username': user['the_name'],
        'photo': photo
    }
    return res


def user_photo(user_photo_id):
    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * FROM User_Photo WHERE user_photo_id = %s''', (user_photo_id,))
    data = cursor.fetchone()
    cursor.close()
    return None if data is None else data['photo']


def address(address_id):
    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * FROM Address WHERE address_id = %s''', (address_id,))
    data = cursor.fetchone()
    cursor.close()

    res = {
        'city': data['city'],
        'district': data['district'],
        'address_details': data['address_details']
    }
    return res


def lost_person(post_id):
    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * FROM Lost_Person WHERE post_id = %s''', (post_id,))
    data = cursor.fetchone()
    cursor.close()

    res = {
        'person_name': data['the_name'],
        'age': data['age'],
        'gender': data['gender']
    }
    return res


def found_person(post_id):
    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * FROM Found_Person WHERE post_id = %s''', (post_id,))
    data = cursor.fetchone()
    cursor.close()

    res = {
        'person_name': data['the_name'],
        'age': data['age'],
        'gender': data['gender']
    }
    return res


def post(post_id):
    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * FROM Post WHERE post_id = %s''', (post_id,))
    data = cursor.fetchone()
    cursor.close()
    return data


def post_main_photo(post_id):
    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT photo FROM Post_Photo WHERE post_id = %s and is_main = true ''', (post_id,))
    cur_photo = cursor.fetchone()
    cursor.close()

    main_photo = None
    if cur_photo:
        main_photo = cur_photo['photo']
    return main_photo


def post_extra_photos(post_id):
    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT photo FROM Post_Photo WHERE post_id = %s and is_main = false ''', (post_id,))
    photos = []
    cur_photo = cursor.fetchone()
    while cur_photo:
        if cur_photo['photo'] is not None:
            photos.append(cur_photo['photo'])
        cur_photo = cursor.fetchone()
    cursor.close()
    return photos


def comment(comment_id):
    cursor = mysql.connection.cursor()
    cursor.execute(''' SELECT * FROM Comment WHERE comment_id = %s''', (comment_id,))
    data = cursor.fetchone()
    cursor.close()
    return data


def post_comments(post_id):
    cursor = mysql.connection.cursor()
    cursor.execute('''SELECT * FROM Comment WHERE post_id = %s ORDER BY parent_id ASC''', (post_id,))
    main_comments = {}
    cur_comment = cursor.fetchone()
    while cur_comment:
        comment_id = cur_comment['comment_id'];
        parent_id = cur_comment['parent_id'];
        content = cur_comment['content']
        user_id = cur_comment['user_id']

        user_data = user(user_id)

        if parent_id == 0:
            main_comments[comment_id] = []
        else:
            main_comments[parent_id].append({
                'id': comment_id,
                'username': user_data['username'],
                'photo': user_data['photo'],
                'Content': content,
            })
        cur_comment = cursor.fetchone()

    all_comments = []
    ids_lst = main_comments.keys()
    for id in ids_lst:
        replies = main_comments[id]

        cursor.execute('''SELECT content, user_id FROM Comment WHERE comment_id = %s''', (id,))
        data = cursor.fetchone()
        content, user_id = data['content'], data['user_id']

        user_data = user(user_id)

        cur_comment_data = {
            'id': id,
            'username': user_data['username'],
            'photo': user_data['photo'],
            'Content': content,
            'replies': replies
        }
        all_comments.append(cur_comment_data)

    cursor.close()
    return all_comments


def posts(cursor, cur_user_id, start, limit, full_data):

    all_posts = []
    cur_post = cursor.fetchone()

    while cur_post:
        # processing one post
        cur_post_data = {}

        user_data = user(cur_post['user_id'])

        reported_person_data = lost_person(cur_post['post_id']) if cur_post['is_lost'] else found_person(cur_post['post_id'])
        reported_person_data['address'] = address(cur_post['address_id'])
        reported_person_data['main_photo'] = post_main_photo(cur_post['post_id'])

        if full_data:
            reported_person_data['extra_photos'] = post_extra_photos(cur_post['post_id'])

        cur = mysql.connection.cursor()
        cur.execute(''' SELECT * from Saved_Posts WHERE user_id = %s and post_id = %s ''',(cur_user_id, cur_post['post_id'],))
        is_saved = cur.fetchone()
        cur.close()

        cur_post_data = {
            'post_id': cur_post['post_id'],
            'user_id': cur_post['user_id'],
            'username': user_data['username'],
            "user_phone_number": user_data['phone_number'],
            'user_photo': user_data['photo'],
            'is_lost': cur_post['is_lost'] == 1,
            'person_data': reported_person_data,
            'details': cur_post['more_details'],
            'is_owner': cur_user_id == cur_post['user_id'],
            'is_saved': is_saved is not None,
            "date": cur_post['date_AND_time']
        }

        if full_data:
            cur_post_data['comments'] = post_comments(cur_post['post_id'])

        all_posts.append(cur_post_data)
        cur_post = cursor.fetchone()

    cursor.close()

    if full_data:
        return make_response(jsonify({
            'post': cur_post_data,
            'status': 200
        })), 200
    else:
        return make_response(jsonify({
            'posts': all_posts[start: start + limit],
            'status': 200
        })), 200