import re
import concurrent.futures
import functools
import threading
import tempfile
from pathlib import Path, PurePath
from hashlib import md5
from flask import request, Blueprint, current_app, flash, get_flashed_messages
from . import PAGE_CACHE

v1 = Blueprint('v1', __name__, url_prefix='/v1')
hash_reg = re.compile("[a-f0-9]{32}")
_og_lock = threading.Lock()


@functools.cache
def overlay_generator():
    if _og_lock.locked():
        # await until the first call completes
        with _og_lock:
            return overlay_generator()
    with _og_lock:
        # This take way too long to import
        from mokuro import OverlayGenerator
        og = OverlayGenerator()

        return og


def manga_page_ocr(*args, **kwargs):
    og = overlay_generator()
    if og.mpocr is None:
        with _og_lock:
            # This take way too long to init
            og.init_models()
    return og.mpocr(*args, **kwargs)


@v1.post('/new-hashes')
def hash_check():
    if not (
        request.is_json and
        isinstance(request.json, list) and
        all(request.json) and
        all(map(lambda hs: isinstance(hs, str), request.json)) and
        all(map(lambda hs: hash_reg.fullmatch(hs.lower()), request.json))
    ):
        return {"error": "Only JSON arrays of MD5 hashes are accepted"}, 415

    new = [
        hs for hs in request.json
        if not current_app.extensions[PAGE_CACHE].has(hs.lower())
    ]

    return {"new": new}


@v1.post('/new_pages')
def new_pages():
    MAX_IMAGE_SIZE = current_app.config["MAX_IMAGE_SIZE"]
    STRICT_NEW_IMAGES = current_app.config["STRICT_NEW_IMAGES"]

    # TODO: improve flashing images to include file name

    e_too_large = f"File size is too large. At most {MAX_IMAGE_SIZE} bytes are accepted"
    e_file_empty = "Empty file was uploaded"
    e_not_image = "Files need to be images"
    e_already_have = "We already have the page in cache"
    e_already_uploaded = "The same page was already uploaded"
    e_unnaceptable = "Ignoring new images because of unacceptable client error"

    jobs = {}

    if not request.files:
        flash("No files were uploaded", "error")

    for file in request.files.values():
        name = file.name

        if file.content_length and file.content_length > MAX_IMAGE_SIZE:
            flash(e_too_large, "error")
            continue
        if file.mimetype and not file.mimetype.startswith("image/"):
            flash(e_not_image, "error")
            continue

        blob = file.read()
        flash(f'Uploaded file "{name}" successfully', "info")

        if not blob:
            flash(e_file_empty, "error")
            continue

        if len(blob) > MAX_IMAGE_SIZE:
            flash(e_too_large, "error")
            if STRICT_NEW_IMAGES:
                flash(e_unnaceptable, "error")
                break
            continue

        hs = md5(blob).hexdigest()

        if hs in jobs:
            flash(e_already_uploaded, "error")
            if STRICT_NEW_IMAGES:
                flash(e_unnaceptable, "error")
                break
            continue

        if current_app.extensions[PAGE_CACHE].has(hs):
            flash(e_already_have, "error")
            if STRICT_NEW_IMAGES:
                flash(e_unnaceptable, "error")
                break
            continue

        temp_file = tempfile.NamedTemporaryFile(prefix="mokuro_page_")
        temp_file.write(blob)
        jobs[hs] = (hs, name, temp_file)

    futures = [
        current_app.extensions["executor"].submit(do_page_ocr, *job)
        for job in jobs.values()
    ]

    for future in concurrent.futures.as_completed(futures):
        hs, name, result = future.result()
        if "error" in result:
            flash(f'Failed OCR of "{name}":' + result["error"], "info")
        else:
            flash(f'Finished OCR of "{name}" successfully', "info")
            current_app.extensions[PAGE_CACHE].set(hs, result)

    if futures:
        flash(f'Finished OCR of all {len(futures)} files', "info")
    else:
        flash('No files were processed', "info")

    return get_flashed_messages(with_categories=True)


@v1.get('/make_html')
def make_html():
    if not (
        request.is_json and
        "title" in request.json and
        "pages" in request.json and
        isinstance(request.json["title"], str) and
        isinstance(request.json["pages"], dict) and
        request.json["title"].strip() and
        request.json["pages"] and
        all(map(lambda s: isinstance(s, str) and s.strip(), request.json["pages"].values())) and
        all(map(lambda hs: hash_reg.fullmatch(hs.lower()),
                request.json["pages"].keys()))
    ):
        return {"error": 'Only non-empty JSON objects accepted.\nSchema: { "title": "file_title", "pages": {img_hash: img_path}}'}, 415

    title = request.json["title"].strip()
    pages = dict(zip(
        map(lambda s: s.strip(), request.json["pages"].values()),
        current_app.extensions[PAGE_CACHE].get_many(
            *request.json["pages"].keys())
    ))

    if not all(pages.values()):
        return {"error": "Asked for page not in cache"}, 400

    try:
        og = overlay_generator()
        page_htmls = [
            og.get_page_html(image_result, PurePath(image_path))
            for image_path, image_result in pages.items()
        ]
        return og.get_index_html(page_htmls, f'{title} | mokuro', True, False)

    except Exception as e:
        return {"error": str(e)}, 400


def do_page_ocr(hs, name, temp_file):
    try:
        path = Path(temp_file.name)

        if not path.exists():
            raise Exception("Internal Server Error: path doesn't exists")
        if not path.is_file():
            raise Exception("Internal Server Error: path is not a file")

        flash(f'Starting OCR of "{name}"', "info")

        return hs, name, manga_page_ocr(path)
    except Exception as e:
        return hs, name, {"error": str(e)}
    finally:
        # either way, when temp_file is garbage collected, it will be deleted
        temp_file.close()
