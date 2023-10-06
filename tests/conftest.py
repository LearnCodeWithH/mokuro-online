import pytest
from app import create_app, OCR_CACHE
from flask import url_for


@pytest.fixture()
def app():
    app = create_app("testing")
    app.secret_key = b"dummy_key"
    with app.test_request_context():
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
    return app.extensions[OCR_CACHE]


# Urls

@pytest.fixture()
def url_hash_check(app):
    return url_for("v1.hash_check")


@pytest.fixture()
def url_new_pages(app):
    return url_for("v1.new_pages")


@pytest.fixture()
def url_make_html(app):
    return url_for("v1.make_html")
