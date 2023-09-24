import re
from hashlib import md5
from flask import request, Blueprint, current_app
from werkzeug.utils import secure_filename
from markupsafe import escape
from . import cache

v1 = Blueprint('v1', __name__, url_prefix='/v1')
hash_reg = re.compile("[a-f0-9]{32}")


@v1.post('/new-hashes')
def hash_check():
    if not (
        request.is_json and
        isinstance(request.json, list) and
        all(request.json) and
        all(map(lambda e: isinstance(e, str), request.json))
    ):
        return {"error": "Only JSON arrays of MD5 hashes are accepted"}, 415

    strict_hashes = bool(current_app.config["STRICT_HASHES"])

    new = []

    for hs in request.json:
        hs_lower = hs.lower()
        if not hash_reg.fullmatch(hs_lower):
            if strict_hashes:
                return {"error": "Invalid MD5 hash was given"}, 400
        elif not cache.has(hs_lower):  # TODO: check queue as well
            new.append(hs)

    return {"new": new}


@v1.post('/new_pages')
def new_pages():
    if not request.files:
        return {"error": "No files were uploaded"}, 415

    MAX_IMAGE_SIZE = current_app.config["MAX_IMAGE_SIZE"]
    STRICT_NEW_IMAGES = current_app.config["STRICT_NEW_IMAGES"]

    e_too_large = (
        {"error": f"File size is too large. At most {MAX_IMAGE_SIZE} bytes are accepted"}, 415)
    e_file_empty = ({"error": "Empty file was uploaded"}, 415)
    e_not_image = ({"error": "Files need to be images"}, 415)
    e_already_have = (
        {"error": "We already have the page. You must only upload brand new pages"}, 415)

    # first pass
    for file in request.files.values():
        if file.content_length and file.content_length > MAX_IMAGE_SIZE:
            return e_too_large
        if file.mimetype and not file.mimetype.startswith("image/"):
            return e_not_image

    for file in request.files.values():
        blob = file.read()
        if not blob:
            return e_file_empty
        if len(blob) > MAX_IMAGE_SIZE:
            return e_too_large

        hs = md5(blob).hexdigest()
        if cache.has(hs):  # TODO: check queue as well
            if STRICT_NEW_IMAGES:
                return e_already_have
            continue

        # TODO: add to job queue
        cache.set(hs, "DUMMY")

    return {}


@v1.get('/make_html')
def make_html():
    return {
        "AWD!@#SDAwd": {"result": "adwdawdawd"}
    }
