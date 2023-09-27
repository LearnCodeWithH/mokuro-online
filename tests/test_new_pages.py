import io
from pathlib import Path
from hashlib import md5
from app.routes import manga_page_ocr

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


def test_ocr_works_page1():
    result = manga_page_ocr(p1)
    assert "blocks" in result
    assert "たすけて" in "".join(flat_map(lambda b: b['lines'], result["blocks"]))


def test_ocr_works_page2():
    result = manga_page_ocr(p2)
    # sometimes it finds something that is not text, like "・"
    assert "blocks" in result
    assert 3 > len("".join(flat_map(lambda b: b['lines'], result["blocks"])))


def test_new_pages_error_no_files(client, url_new_pages):
    res = client.post(url_new_pages, data={})
    assert 1 == len(tuple(filter(lambda msg: msg[0] == "error", res.json)))
    error = next((msg for msg in res.json if msg[0] == "error"), None)
    assert "files" in error[1].lower()


def test_new_pages_error_empty_file(client, url_new_pages):
    data = {"file.png": (io.BytesIO(b""), "file.png", "image/png")}
    res = client.post(url_new_pages, data=data)
    assert 1 == len(tuple(filter(lambda msg: msg[0] == "error", res.json)))
    error = next((msg for msg in res.json if msg[0] == "error"), None)
    assert "empty" in error[1].lower()


def test_new_pages_error_large_file(client, url_new_pages, app):
    app.config.update(MAX_IMAGE_SIZE=5)
    data = {"file.png": (io.BytesIO(b"123456789"), "file.png", "image/png")}
    res = client.post(url_new_pages, data=data)
    assert 1 == len(tuple(filter(lambda msg: msg[0] == "error", res.json)))
    error = next((msg for msg in res.json if msg[0] == "error"), None)
    assert "large" in error[1].lower()


def test_new_pages_error_not_image(client, url_new_pages):
    data = {"file.html": (io.BytesIO(b"123456789"), "file.html", "text/html")}
    res = client.post(url_new_pages, data=data)
    assert 1 == len(tuple(filter(lambda msg: msg[0] == "error", res.json)))
    error = next((msg for msg in res.json if msg[0] == "error"), None)
    assert "image" in error[1].lower()


def test_new_pages_error_already_have(client, url_new_pages, cache, app):
    app.config.update(STRICT_NEW_IMAGES=True)

    hs = md5(p1.read_bytes()).hexdigest()
    cache.set(hs, "DUMMY")

    data = {p1.name: (p1.open("rb"), p1.name)}
    res = client.post(url_new_pages, data=data)

    assert 2 == len(tuple(filter(lambda msg: msg[0] == "error", res.json)))
    error = next((msg for msg in res.json if msg[0] == "error"), None)
    assert "already" in error[1].lower()


def test_new_pages_non_stop_already_have(client, url_new_pages, cache):
    hs = md5(p1.read_bytes()).hexdigest()
    cache.set(hs, "DUMMY")

    data = {p1.name: (p1.open("rb"), p1.name)}
    res = client.post(url_new_pages, data=data)

    assert 1 == len(tuple(filter(lambda msg: msg[0] == "error", res.json)))
    error = next((msg for msg in res.json if msg[0] == "error"), None)
    assert "already" in error[1].lower()


def test_new_pages_error_file_twice(client, url_new_pages, cache, app):
    app.config.update(STRICT_NEW_IMAGES=True)

    hs = md5(p1.read_bytes()).hexdigest()

    data = {
        p1.name: (p1.open("rb"), p1.name),
        "copy_" + p1.name: (p1.open("rb"), "copy_" + p1.name),
    }
    res = client.post(url_new_pages, data=data)

    assert 2 == len(tuple(filter(lambda msg: msg[0] == "error", res.json)))
    error = next((msg for msg in res.json if msg[0] == "error"), None)
    assert "already" in error[1].lower()

    assert cache.has(hs)
    result = cache.get(hs)
    assert "blocks" in result
    assert "たすけて" in "".join(flat_map(lambda b: b['lines'], result["blocks"]))


def test_new_pages_non_stop_file_twice(client, url_new_pages, cache, app):
    hs = md5(p1.read_bytes()).hexdigest()

    data = {
        p1.name: (p1.open("rb"), p1.name),
        "copy_" + p1.name: (p1.open("rb"), "copy_" + p1.name),
    }
    res = client.post(url_new_pages, data=data)

    assert 1 == len(tuple(filter(lambda msg: msg[0] == "error", res.json)))
    error = next((msg for msg in res.json if msg[0] == "error"), None)
    assert "already" in error[1].lower()

    assert cache.has(hs)
    result = cache.get(hs)
    assert "blocks" in result
    assert "たすけて" in "".join(flat_map(lambda b: b['lines'], result["blocks"]))


def test_new_pages_multiple_work(client, url_new_pages, cache, app):
    app.config.update(STRICT_NEW_IMAGES=True)

    data = {
        p1.name: (p1.open("rb"), p1.name),
        p2.name: (p2.open("rb"), p2.name),
    }
    res = client.post(url_new_pages, data=data)

    hs = md5(p1.read_bytes()).hexdigest()
    assert cache.has(hs)
    result = cache.get(hs)
    assert "blocks" in result
    assert "たすけて" in "".join(flat_map(lambda b: b['lines'], result["blocks"]))

    hs = md5(p2.read_bytes()).hexdigest()
    assert cache.has(hs)
    result = cache.get(hs)
    assert "blocks" in result
    # sometimes it finds something that is not text, like "・"
    assert 5 > len("".join(flat_map(lambda b: b['lines'], result["blocks"])))
