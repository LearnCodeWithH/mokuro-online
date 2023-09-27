import json
from pathlib import Path, PurePath

tc = Path(__file__).parent / "res/test_chapter.json"


def test_make_html_need_json(client, url_make_html):
    res = client.get(url_make_html)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_empty(client, url_make_html):
    data = {}
    res = client.get(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_no_title(client, url_make_html):
    data = {"pages": {}}
    res = client.get(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_no_pages(client, url_make_html):
    data = {"title": "Chapter 1.1"}
    res = client.get(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_title_non_string(client, url_make_html):
    data = {"pages": {}, "title": 123}
    res = client.get(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_title_empty(client, url_make_html):
    data = {"pages": {}, "title": "   "}
    res = client.get(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_empty_pages(client, url_make_html):
    data = {"title": "Chapter 1.1", "pages": {}}
    res = client.get(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_invalid_hash(client, url_make_html):
    data = {"title": "Chapter 1.1", "pages": {"invalid": "value"}}
    res = client.get(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_non_string_path(client, url_make_html):
    data = {"title": "Chapter 1.1", "pages": {f"{1:032}": 123}}
    res = client.get(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_empty_string_path(client, url_make_html):
    data = {"title": "Chapter 1.1", "pages": {f"{1:032}": "   "}}
    res = client.get(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_not_in_cache(client, url_make_html):
    data = {"title": "Chapter 1.1", "pages": {f"{1:032}": "page1.jpg"}}
    res = client.get(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_simple_works(client, url_make_html, cache):
    key = f"{1:032}"
    cache.set(key, {"version": "0.1.7", "img_width": 1350,
              "img_height": 1920, "blocks": []})

    data = {"title": "Chapter 1.1", "pages": {key: "page1.jpg"}}
    res = client.get(url_make_html, json=data)
    assert res.status_code == 200


def test_make_html_simple_is_same(client, url_make_html, cache):
    from app.routes import overlay_generator

    key = f"{1:032}"
    value = {"version": "0.1.7", "img_width": 1350,
             "img_height": 1920, "blocks": []}
    cache.set(key, value)
    data = {"title": "Chapter 1.1", "pages": {key: "page1.jpg"}}
    res = client.get(url_make_html, json=data)
    assert res.status_code == 200

    og = overlay_generator()
    page_htmls = [og.get_page_html(value, PurePath("page1.jpg"))]
    html = og.get_index_html(page_htmls, f'Chapter 1.1 | mokuro', True, False)

    assert res.text == html


def test_make_html_works(client, url_make_html, cache):
    test_chapter = json.load(open(tc, "r"))
    cache.set_many(test_chapter)
    pages = {key: f"{int(key):02}.jpg" for key in test_chapter}
    data = {"title": "Chapter 1.1", "pages": pages}
    res = client.get(url_make_html, json=data)
    assert res.status_code == 200
