from flask import Flask
from flask_caching import Cache
from flask_executor import Executor
from .db import SqliteCache
import config
import threading
import os

OCR_CACHE = "OCR_CACHE"


def create_app(config_env=None):
    app = Flask(__name__)

    if config_env is None:
        config_env = os.environ.get("MOKURO_ONLINE_ENV", "dev")

    if not isinstance(config_env, str):
        # if not a string, it's a object
        app.config.from_object(config_env)
    else:
        if config_env == "production":
            app.config.from_object(config.ProductionConfig)
        elif config_env == "local":
            app.config.from_object(config.LocalConfig)
        elif config_env == "testing":
            app.config.from_object(config.TestingConfig)
        else:
            config_env = "development"
            app.config.from_object(config.DevelopmentConfig)
        # TODO: log config_env

    app.config.from_prefixed_env(prefix="MOKURO_ONLINE")

    assert app.secret_key, "The app secret key was not configured."

    Executor(app)
    app.extensions[OCR_CACHE] = Cache(app, config={
        key.removeprefix("OCR_"): app.config[key]
        for key in app.config.keys() if key.startswith("OCR_CACHE_")})

    with app.app_context():
        app.queue = dict()
        app.queue_lock = threading.Lock()

    from . import routes
    app.register_blueprint(routes.v1)
    app.register_blueprint(routes.site)

    return app
