import io
from pathlib import Path
from hashlib import md5
from app import manga_page_ocr

test_dir = Path(__file__).parent
p1 = Path(__file__).parent / "res/page1.webp"
p2 = Path(__file__).parent / "res/page2.jpg"


def flat_map(f, xs):
    ys = []
    for x in xs:
        ys.extend(f(x))
    return ys


def test_files_exist():
    assert p1.exists()
    assert p2.exists()


def test_new_pages_error_no_files(client, url_new_pages):
    res = client.post(url_new_pages, data={})
    assert 1 == len(tuple(filter(lambda msg: msg[0] == "error", res.json)))
    error = next((msg for msg in res.json if msg[0] == "error"), None)
    assert "files" in error[1].lower()


def test_new_pages_error_empty_file(client, url_new_pages):
    data = {f"{1:032}": (io.BytesIO(b""), "file.png", "image/png")}
    res = client.post(url_new_pages, data=data)
    assert 1 == len(tuple(filter(lambda msg: msg[0] == "error", res.json)))
    error = next((msg for msg in res.json if msg[0] == "error"), None)
    assert "empty" in error[1].lower()


def test_new_pages_error_large_file(client, url_new_pages, app):
    app.config.update(MAX_IMAGE_SIZE=5)
    data = {f"{1:032}": (io.BytesIO(b"123456789"), "file.png", "image/png")}
    res = client.post(url_new_pages, data=data)
    assert 1 == len(tuple(filter(lambda msg: msg[0] == "error", res.json)))
    error = next((msg for msg in res.json if msg[0] == "error"), None)
    assert "large" in error[1].lower()


def test_new_pages_error_not_image(client, url_new_pages):
    data = {f"{1:032}": (io.BytesIO(b"123456789"), "file.html", "text/html")}
    res = client.post(url_new_pages, data=data)
    assert 1 == len(tuple(filter(lambda msg: msg[0] == "error", res.json)))
    error = next((msg for msg in res.json if msg[0] == "error"), None)
    assert "image" in error[1].lower()


def test_new_pages_error_key_not_hash(client, url_new_pages, cache, app):
    data = {"INVALID_HASH": (p1.open("rb"), p1.name)}
    res = client.post(url_new_pages, data=data)

    assert 1 == len(tuple(filter(lambda msg: msg[0] == "error", res.json)))
    error = next((msg for msg in res.json if msg[0] == "error"), None)
    assert "key" in error[1].lower()
    assert "hash" in error[1].lower()


def test_new_pages_error_hash_no_match(client, url_new_pages, cache, app):
    data = {f"{1:032}": (p1.open("rb"), p1.name)}
    res = client.post(url_new_pages, data=data)

    assert 1 == len(tuple(filter(lambda msg: msg[0] == "error", res.json)))
    error = next((msg for msg in res.json if msg[0] == "error"), None)
    assert "hash" in error[1].lower()


def test_new_pages_multiple_work(client, url_new_pages, cache, app):
    hs1 = md5(p1.read_bytes()).hexdigest()
    hs2 = md5(p2.read_bytes()).hexdigest()

    data = {
        hs1: (p1.open("rb"), p1.name),
        hs2: (p2.open("rb"), p2.name),
    }
    res = client.post(url_new_pages, data=data)

    assert cache.has(hs1)
    result = cache.get(hs1)
    assert "blocks" in result
    assert "たすけて" in "".join(flat_map(lambda b: b['lines'], result["blocks"]))

    assert cache.has(hs2)
    result = cache.get(hs2)
    assert "blocks" in result
    # sometimes it finds something that is not text, like "・"
    assert 5 > len("".join(flat_map(lambda b: b['lines'], result["blocks"])))
