import pytest
from app import create_app, cache as app_cache
from app.config import TestingConfig


@pytest.fixture()
def app():
    app = create_app()
    app.config.from_object(TestingConfig)
    yield app
    # clean up / reset resources here


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture()
def cache(app):
    app_cache.init_app(app)
    return app_cache
