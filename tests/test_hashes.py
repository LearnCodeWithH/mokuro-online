from hashlib import md5


def sh(s):
    return md5(s).hexdigest()


def test_hashes_need_json(client, url_hashes):
    response = client.post(url_hashes)
    assert response.status_code != 200
    assert "error" in response.json


def test_hashes_obj_error(client, url_hashes):
    response = client.post(url_hashes, json={})
    assert response.status_code != 200
    assert "error" in response.json


def test_hashes_nonstring_error(client, url_hashes):
    response = client.post(url_hashes, json=[123])
    assert response.status_code != 200
    assert "error" in response.json


def test_hashes_empty_string_error(client, url_hashes):
    response = client.post(url_hashes, json=[""])
    assert response.status_code != 200
    assert "error" in response.json


def test_hashes_invalid_error(client, url_hashes, app):
    json = [sh(b"1"), "invalid", sh(b"3")]
    response = client.post(url_hashes, json=json)

    assert response.status_code != 200
    assert "error" in response.json


def test_hashes_empty(client, url_hashes):
    response = client.post(url_hashes, json=[])
    assert response.status_code == 200
    assert response.json == {"new": [], "in_queue": [], "in_cache": []}


def test_hashes_all_new(client, url_hashes):
    json = [sh(b"1"), sh(b"2"), sh(b"3")]
    response = client.post(url_hashes, json=json)

    assert response.status_code == 200
    assert response.json == {"new": json, "in_queue": [], "in_cache": []}


def test_hashes_all_cache(client, url_hashes, cache):
    json = [sh(b"1"), sh(b"2"), sh(b"3")]

    for key in json:
        cache.set(key, "DUMMY")
    response = client.post(url_hashes, json=json)

    assert response.status_code == 200
    assert response.json == {"new": [], "in_queue": [], "in_cache": json}


def test_hashes_all_queue(client, url_hashes, app):
    json = [sh(b"1"), sh(b"2"), sh(b"3")]

    for key in json:
        app.queue[key] = "DUMMY"
    response = client.post(url_hashes, json=json)

    assert response.status_code == 200
    assert response.json == {"new": [], "in_queue": json, "in_cache": []}


def test_hashes_some_found(client, url_hashes, cache, app):
    old = list(sorted([sh(b"1"), sh(b"4"), sh(b"7")]))
    que = list(sorted([sh(b"2"), sh(b"5"), sh(b"8")]))
    new = list(sorted([sh(b"3"), sh(b"6"), sh(b"9")]))

    json = list(sorted(old + que + new))

    for key in old:
        cache.set(key, "DUMMY")
    for key in que:
        app.queue[key] = "DUMMY"

    response = client.post(url_hashes, json=json)

    assert response.status_code == 200
    assert response.json == {"new": new, "in_queue": que, "in_cache": old}
