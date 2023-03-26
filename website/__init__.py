from flask import Flask

from .view import *


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '1221200015'


    app.register_blueprint(home, url_prefix='/')

    app.register_blueprint(signup, url_prefix='/')

    app.register_blueprint(login, url_prefix='/')

    app.register_blueprint(heat, url_prefix='/')


    app.register_error_handler(404, page_not_found)


    return app