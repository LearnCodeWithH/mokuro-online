
def test_request_example(client, cache):
    cache.set("foo", "bar")
    response = client.post("/v1/request/foo")
    assert response.text == "bar"
