import io
from pathlib import Path
from hashlib import md5

test_dir = Path(__file__).parent
p = test_dir / "page1.webp"


def test_files_exist():
    assert p.exists()


def test_new_pages_error_no_files(client, url_new_pages):
    res = client.post(url_new_pages, data={})
    assert res.status_code != 200
    assert "error" in res.json


def test_new_pages_error_empty_file(client, url_new_pages):
    res = client.post(url_new_pages, data={
                      "name": (io.BytesIO(b""), "name", "image/png")})
    assert res.status_code != 200
    assert "error" in res.json
    assert "empty" in res.json["error"].lower()


def test_new_pages_error_large_file(client, url_new_pages, app):
    app.config.update(MAX_IMAGE_SIZE=5)
    res = client.post(url_new_pages, data={
                      "name": (io.BytesIO(b"123456789"), "name", "image/png")})
    assert res.status_code != 200
    assert "error" in res.json
    assert "large" in res.json["error"].lower()


def test_new_pages_error_not_image(client, url_new_pages):
    res = client.post(url_new_pages, data={
                      "name": (io.BytesIO(b"123456789"), "name", "text/html")})
    assert res.status_code != 200
    assert "error" in res.json
    assert "image" in res.json["error"].lower()


def test_new_pages_error_already_have(client, url_new_pages, cache, app):
    hs = md5(p.read_bytes()).hexdigest()
    cache.set(hs, "DUMMY")

    app.config.update(STRICT_NEW_IMAGES=True)
    res = client.post(url_new_pages, data={p.name: p.open("rb")})

    assert res.status_code != 200
    assert "error" in res.json


def test_new_pages_non_error_already_have(client, url_new_pages, cache):
    hs = md5(p.read_bytes()).hexdigest()
    cache.set(hs, "DUMMY")

    res = client.post(url_new_pages, data={p.name: p.open("rb")})

    assert res.json == {}
    assert res.status_code == 200


def test_new_pages_error_upload_double(client, url_new_pages, app):
    app.config.update(STRICT_NEW_IMAGES=True)

    res = client.post(url_new_pages, data={p.name: p.open("rb")})
    assert res.json == {}
    assert res.status_code == 200

    res = client.post(url_new_pages, data={p.name: p.open("rb")})
    assert res.status_code != 200
    assert "error" in res.json


def test_new_pages_error_file_twice(client, url_new_pages, app):
    app.config.update(STRICT_NEW_IMAGES=True)

    res = client.post(url_new_pages, data={
                      "1": p.open("rb"), "2": p.open("rb")})
    assert res.status_code != 200
    assert "error" in res.json
