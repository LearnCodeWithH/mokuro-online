from flask import Flask
from flask_caching import Cache
from flask_executor import Executor
from .config import DevelopmentConfig

# TODO: make this non-global
cache = Cache()


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)

    app.config.from_object(config_class)
    app.config.from_envvar('MOKURO_API_SETTINGS', silent=True)

    cache.init_app(app)
    Executor(app)

    from app import routes
    app.register_blueprint(routes.v1)

    return app
