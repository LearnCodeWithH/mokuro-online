from flask import Flask
from flask_caching import Cache
from flask_executor import Executor
from .config import DevelopmentConfig
from .db import SqliteCache
import threading

OCR_CACHE = "OCR_CACHE"


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)

    app.config.from_object(config_class)
    app.config.from_envvar('MOKURO_API_SETTINGS', silent=True)
    app.config.from_prefixed_env(prefix="MOKURO_API")

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
