from flask import Flask, request, Blueprint
from werkzeug.utils import secure_filename
from markupsafe import escape
from . import cache

v1 = Blueprint('v1', __name__, url_prefix='/v1')


@v1.get('/processed')
def processed():
    return {
        "missing": [],
        "found": [],
    }


@v1.post('/request/<key>')
def request(key):
    return str(cache.get(key))


@v1.get('/results')
def results():
    return {
        "AWD!@#SDAwd": {"result": "adwdawdawd"}
    }
