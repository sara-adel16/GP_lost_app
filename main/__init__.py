from flask import Flask
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
SECRET_KEY = os.getenv('SECRET_KEY')
app.config['WTF_CSRF_ENABLED'] = False
app.config['WTF_CSRF_CHECK_DEFAULT'] = False
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'gp=ac123'
app.config['MYSQL_DB'] = 'data_'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)
bcrypt = Bcrypt(app)

from main import routes
from main.routes import auth_blueprint
app.register_blueprint(auth_blueprint)