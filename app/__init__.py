from flask import Flask
from flask_caching import Cache
from flask_executor import Executor
from .config import DevelopmentConfig

PAGE_CACHE = "page_cache"

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)

    app.config.from_object(config_class)
    app.config.from_envvar('MOKURO_API_SETTINGS', silent=True)
    app.config.from_prefixed_env(prefix="MOKURO_API")

    Executor(app)
    app.extensions[PAGE_CACHE] = Cache(app, config={
        key.removeprefix("PAGE_"): app.config[key]
        for key in app.config.keys() if key.startswith("PAGE_CACHE_")})

    from app import routes
    app.register_blueprint(routes.v1)

    return app
