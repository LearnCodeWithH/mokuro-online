from flask import Flask
from flask_caching import Cache
from flask_executor import Executor
from .db import SqliteCache
import config
import threading
import os
import functools
import logging

OCR_CACHE = "OCR_CACHE"
_og_lock = threading.Lock()


@functools.cache
def overlay_generator():
    if _og_lock.locked():
        # await until the first cached call completes
        with _og_lock:
            return overlay_generator()
    with _og_lock:
        # This take way too long to import
        from mokuro import OverlayGenerator
        og = OverlayGenerator()
        return og


def manga_page_ocr(*args, **kwargs):
    og = overlay_generator()
    if og.mpocr is None:
        with _og_lock:
            # This take way too long to init
            og.init_models()
    if not args and not kwargs:
        return
    return og.mpocr(*args, **kwargs)


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

            # TODO: implement proper logging. It shouldn't be mixed
            # add gunicorn logger handlers.
            gunicorn_logger = logging.getLogger('gunicorn.error')
            app.logger.handlers = gunicorn_logger.handlers
            app.logger.setLevel(gunicorn_logger.level)

        elif config_env == "local":
            app.config.from_object(config.LocalConfig)
        elif config_env == "testing":
            app.config.from_object(config.TestingConfig)
        else:
            config_env = "development"
            app.config.from_object(config.DevelopmentConfig)
        app.logger.info(
            f"Starting mokuro-online with {config_env} environment")

    app.config.from_prefixed_env(prefix="MOKURO_ONLINE")

    assert app.secret_key, "The app secret key was not configured."

    Executor(app)
    app.extensions[OCR_CACHE] = Cache(app, config={
        key.removeprefix("OCR_"): app.config[key]
        for key in app.config.keys() if key.startswith("OCR_CACHE_")})

    with app.app_context():
        app.queue = dict()
        app.queue_lock = threading.Lock()
        # preload OCR generator. executor needs a request context to work
        if config_env == "production":
            with app.test_request_context():
                app.extensions["executor"].submit(lambda: manga_page_ocr())

    from . import routes
    app.register_blueprint(routes.v1)
    app.register_blueprint(routes.site)

    return app
