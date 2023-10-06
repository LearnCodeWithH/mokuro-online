import json
from pathlib import Path, PurePath

tc = Path(__file__).parent / "res/test_chapter.json"


def test_make_html_need_json(client, url_make_html):
    res = client.post(url_make_html)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_empty(client, url_make_html):
    data = {}
    res = client.post(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_no_title(client, url_make_html):
    data = {"page_map": []}
    res = client.post(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_no_pages(client, url_make_html):
    data = {"title": "Chapter 1.1"}
    res = client.post(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_title_non_string(client, url_make_html):
    data = {"page_map": [], "title": 123}
    res = client.post(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_title_empty(client, url_make_html):
    data = {"page_map": [], "title": "   "}
    res = client.post(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_empty_pages(client, url_make_html):
    data = {"title": "Chapter 1.1", "page_map": []}
    res = client.post(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_invalid_types(client, url_make_html):
    data = {"title": "Chapter 1.1", "page_map": ["invalid", "value"]}
    res = client.post(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_invalid_hash(client, url_make_html):
    data = {"title": "Chapter 1.1", "page_map": [["invalid", "value"]]}
    res = client.post(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_non_string_path(client, url_make_html):
    data = {"title": "Chapter 1.1", "page_map": [[123, f"{1:032}"]]}
    res = client.post(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_empty_string_path(client, url_make_html):
    data = {"title": "Chapter 1.1", "page_map": [["   ", f"{1:032}"]]}
    res = client.post(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_not_in_cache(client, url_make_html):
    data = {"title": "Chapter 1.1", "page_map": [["page1.jpg", f"{1:032}"]]}
    res = client.post(url_make_html, json=data)
    assert "error" in res.json
    assert res.status_code != 200


def test_make_html_simple_works(client, url_make_html, cache):
    hs = f"{1:032}"
    cache.set(hs, {"version": "0.1.7", "img_width": 1350,
              "img_height": 1920, "blocks": []})

    data = {"title": "Chapter 1.1", "page_map": [["page1.jpg", hs]]}
    res = client.post(url_make_html, json=data)
    assert res.status_code == 200, res.json["error"]


def test_make_html_works(client, url_make_html, cache):
    test_chapter = json.load(open(tc, "r"))
    cache.set_many(test_chapter)
    pages = [[f"{int(hs):02}.jpg", hs] for hs in test_chapter]
    data = {"title": "Chapter 1.1", "page_map": pages}
    res = client.post(url_make_html, json=data)
    assert res.status_code == 200, res.json["error"]
