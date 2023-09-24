import re
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
        elif not cache.has(hs_lower):
            new.append(hs)

    return {"new": new}


@v1.post('/new_images')
def new_images():
    return {}


@v1.get('/make_html')
def make_html():
    return {
        "AWD!@#SDAwd": {"result": "adwdawdawd"}
    }
