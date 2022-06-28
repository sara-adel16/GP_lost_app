CREATE DATABASE IF NOT exists data_ DEFAULT CHARACTER SET utf8 COLLATE utf8_general_ci;
USE data_;

SET @@global.sql_mode= '';

CREATE TABLE IF NOT EXISTS Address (
	address_id INT NOT NULL AUTO_INCREMENT,
	city VARCHAR(50),
	district VARCHAR(50),
    address_details text,
	PRIMARY KEY (address_id)
);

CREATE TABLE IF NOT EXISTS User_Photo (
	user_photo_id int NOT NULL AUTO_INCREMENT,
	photo BLOB,
	PRIMARY KEY (user_photo_id)
);

CREATE TABLE IF NOT EXISTS User (
	user_id INT NOT NULL AUTO_INCREMENT,
	the_name VARCHAR(50) NOT NULL,
	phone_number VARCHAR(50) NOT NULL,
	the_password VARCHAR(255) NOT NULL,
	email VARCHAR(255),
    fcm_token text NOT NULL,
	user_photo_id INT,
	PRIMARY KEY (user_id),
	FOREIGN KEY (user_photo_id) REFERENCES User_Photo(user_photo_id)
);

CREATE TABLE IF NOT EXISTS Post (
	post_id INT NOT NULL AUTO_INCREMENT,
    is_lost bool NOT NULL,
    is_temp bool NOT NULL,
	more_details TEXT,
	date_AND_time timestamp NOT NULL,
	address_id INT NOT NULL,
	user_id INT NOT NULL,
	PRIMARY KEY (post_id),
	FOREIGN KEY (user_id) REFERENCES User(user_id),
	FOREIGN KEY (address_id) REFERENCES Address(address_id)
);

CREATE TABLE IF NOT EXISTS Post_Photo (
	post_photo_id int NOT NULL AUTO_INCREMENT,
	post_id int NOT NULL,
	photo BLOB,
	is_main bool NOT NULL,
    is_temp bool NOT NULL,
    PRIMARY KEY (post_photo_id),
	FOREIGN KEY (post_id) REFERENCES Post(post_id)
);

CREATE TABLE IF NOT EXISTS Comment (
	comment_id INT NOT NULL AUTO_INCREMENT,
    parent_id INT NOT NULL,
	content TEXT NOT NULL,
	date_AND_time timestamp NOT NULL,
	user_id INT NOT NULL,
	post_id INT NOT NULL,
	PRIMARY KEY (comment_id),
	FOREIGN KEY (user_id) REFERENCES User(user_id),
	FOREIGN KEY (post_id) REFERENCES Post(post_id)
);

CREATE TABLE IF NOT EXISTS Lost_Person (
	person_id INT NOT NULL AUTO_INCREMENT,
	the_name VARCHAR(50),
	age INT,
	gender VARCHAR(10),
	post_id INT NOT NULL,
    is_temp bool NOT NULL,
	PRIMARY KEY (person_id),
	FOREIGN KEY (post_id) REFERENCES Post(post_id)
);

CREATE TABLE IF NOT EXISTS Found_Person (
	person_id INT NOT NULL AUTO_INCREMENT,
	the_name VARCHAR(50),
	age INT,
	gender VARCHAR(10),
	post_id INT NOT NULL,
    is_temp bool NOT NULL,
	PRIMARY KEY (person_id),
	FOREIGN KEY (post_id) REFERENCES Post(post_id)
);

CREATE TABLE IF NOT EXISTS Saved_Posts (
	user_id INT NOT NULL,
	post_id INT NOT NULL,
	FOREIGN KEY (user_id) REFERENCES User(user_id),
	FOREIGN KEY (post_id) REFERENCES Post(post_id)
);

CREATE TABLE IF NOT EXISTS Notifications (
	no_id INT NOT NULL AUTO_INCREMENT,
	user_id INT NOT NULL,
	user_photo_id INT,
    post_photo_id INT NOT NULL,
    title text not NULL,
    msg text not NULL,
    PRIMARY KEY (no_id),
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);