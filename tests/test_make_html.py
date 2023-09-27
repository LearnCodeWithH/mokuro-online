import json
from pathlib import Path
# import io
# from hashlib import md5
# from app.routes import overlay_generator

tc = Path(__file__).parent / "res/test_chapter.json"


def test_files_exist():
    assert tc.exists()
    assert json.load(open(tc, "r"))


# def test_ocr_works_page1():
#     result = overlay_generator().mpocr(p1)
#     assert "blocks" in result
#     assert "たすけて" in "".join(flat_map(lambda b: b['lines'], result["blocks"]))


def test_make_html_need_json(client, url_make_html):
    response = client.get(url_make_html)
    assert "error" in response.json
    assert response.status_code != 200


def test_make_html_empty(client, url_make_html):
    response = client.get(url_make_html, json={})
    assert "error" in response.json
    assert response.status_code != 200


def test_make_html_invalid_hash(client, url_make_html):
    response = client.get(url_make_html, json={"invalid": "value"})
    assert "error" in response.json
    assert response.status_code != 200


def test_make_html_non_string_path(client, url_make_html):
    response = client.get(url_make_html, json={f"{1:032}": 123})
    assert "error" in response.json
    assert response.status_code != 200


def test_make_html_empty_string_path(client, url_make_html):
    response = client.get(url_make_html, json={f"{1:032}": ""})
    assert "error" in response.json
    assert response.status_code != 200


def test_make_html_not_in_cache(client, url_make_html):
    response = client.get(url_make_html, json={f"{1:032}": "page1.jpg"})
    assert "error" in response.json
    assert response.status_code != 200


def test_make_html_simple_works(client, url_make_html, cache):
    key = f"{1:032}"
    cache.set(key, {"version": "0.1.7", "img_width": 1350,
              "img_height": 1920, "blocks": []})

    response = client.get(url_make_html, json={key: "page1.jpg"})
    assert {} == response.json
    assert response.status_code == 200
