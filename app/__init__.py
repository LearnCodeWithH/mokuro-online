from flask import Flask
from flask_caching import Cache
from flask_executor import Executor
from .db import SqliteCache
import config
import threading
import os

OCR_CACHE = "OCR_CACHE"


def create_app(config_class=None):
    app = Flask(__name__)

    env = os.environ.get("MOKURO_ONLINE_ENV")
    if config_class is not None:
        app.config.from_object(config_class)
    elif env == "production":
        app.config.from_object(config.ProductionConfig)
    elif env == "local":
        app.config.from_object(config.LocalConfig)
    elif env == "testing":
        app.config.from_object(config.TestingConfig)
    else:
        app.config.from_object(config.DevelopmentConfig)

    app.config.from_prefixed_env(prefix="MOKURO_ONLINE")

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
