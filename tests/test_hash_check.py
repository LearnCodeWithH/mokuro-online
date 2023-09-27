from hashlib import md5


def sh(s):
    return md5(s).hexdigest()


def test_hash_check_need_json(client, url_hash_check):
    response = client.post(url_hash_check)
    assert response.status_code != 200
    assert "error" in response.json


def test_hash_check_obj_error(client, url_hash_check):
    response = client.post(url_hash_check, json={})
    assert response.status_code != 200
    assert "error" in response.json


def test_hash_check_nonstring_error(client, url_hash_check):
    response = client.post(url_hash_check, json=[123])
    assert response.status_code != 200
    assert "error" in response.json


def test_hash_check_empty_string_error(client, url_hash_check):
    response = client.post(url_hash_check, json=[""])
    assert response.status_code != 200
    assert "error" in response.json


def test_hash_check_invalid_error(client, url_hash_check, app):
    json = [sh(b"1"), "invalid", sh(b"3")]
    response = client.post(url_hash_check, json=json)

    assert response.status_code != 200
    assert "error" in response.json


def test_hash_check_empty(client, url_hash_check):
    response = client.post(url_hash_check, json=[])
    assert response.status_code == 200
    assert response.json == {"new": []}


def test_hash_check_none_found(client, url_hash_check):
    json = [sh(b"1"), sh(b"2"), sh(b"3")]
    response = client.post(url_hash_check, json=json)

    assert response.status_code == 200
    assert response.json == {"new": json}


def test_hash_check_all_found(client, url_hash_check, cache):
    json = [sh(b"1"), sh(b"2"), sh(b"3")]

    for key in json:
        cache.set(key, "DUMMY")
    response = client.post(url_hash_check, json=json)

    assert response.status_code == 200
    assert response.json == {"new": []}


def test_hash_check_some_found(client, url_hash_check, cache):
    old = list(sorted([sh(b"1"), sh(b"3"), sh(b"5")]))
    new = list(sorted([sh(b"2"), sh(b"4"), sh(b"6")]))
    json = list(sorted(old + new))

    for key in old:
        cache.set(key, "DUMMY")

    response = client.post(url_hash_check, json=json)

    assert response.status_code == 200
    assert response.json == {"new": new}
