import pytest
from app import create_app, cache as app_cache
from app.config import TestingConfig
from flask import url_for


@pytest.fixture()
def app():
    app = create_app(TestingConfig)
    yield app
    # clean up / reset resources here


@pytest.fixture()
def ctx(app):
    return app.test_request_context()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


@pytest.fixture()
def cache(app):
    return app_cache

# Urls


@pytest.fixture()
def url_hash_check(ctx):
    with ctx:
        return url_for("v1.hash_check")


@pytest.fixture()
def url_new_pages(ctx):
    with ctx:
        return url_for("v1.new_pages")


@pytest.fixture()
def url_make_html(ctx):
    with ctx:
        return url_for("v1.make_html")
