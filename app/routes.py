import json
import re
import concurrent.futures
import functools
import threading
import tempfile
from pathlib import Path, PurePath
from hashlib import md5
from flask import request, Response, Blueprint, current_app, flash, get_flashed_messages, stream_with_context
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


@v1.post('/hash_check')
def hash_check():
    if not (request.is_json and valid_hash_list(request.json)):
        return {"error": "Only JSON arrays of MD5 hashes are accepted"}, 415

    new = tuple(
        hs for hs in dict.fromkeys(request.json)
        if not current_app.extensions[PAGE_CACHE].has(hs.lower())
    )

    return {"new": new}


@v1.post('/ocr')
def ocr():
    if not (request.is_json and valid_hash_list(request.json)):
        return {"error": "Only JSON arrays of MD5 hashes are accepted"}, 415

    hashes = tuple(hs for hs in dict.fromkeys(request.json))
    results = current_app.extensions[PAGE_CACHE].get_many(
        *map(lambda hs: hs.lower(), hashes))

    ocr = {hs: rs for hs, rs in zip(hashes, results) if rs != None}
    new = tuple(hs for hs, rs in zip(hashes, results) if rs == None)

    return {"ocr": ocr, "new": new}


@v1.post('/new_pages')
@stream_with_context
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

    def cflash(msg, cat):
        flash(msg, cat)
        return json.dumps([str(msg), str(cat)], ensure_ascii=False) + '\n'

    def function_results():
        jobs = {}

        if not request.files:
            yield cflash("No files were uploaded", "error")

        for file in request.files.values():
            name = file.name

            if file.content_length and file.content_length > MAX_IMAGE_SIZE:
                yield cflash(e_too_large, "error")
                continue
            if file.mimetype and not file.mimetype.startswith("image/"):
                yield cflash(e_not_image, "error")
                continue

            blob = file.read()
            yield cflash(f'Uploaded file "{name}" successfully', "success")

            if not blob:
                yield cflash(e_file_empty, "error")
                continue

            if len(blob) > MAX_IMAGE_SIZE:
                yield cflash(e_too_large, "error")
                if STRICT_NEW_IMAGES:
                    yield cflash(e_unnaceptable, "error")
                    break
                continue

            hs = md5(blob).hexdigest()

            if hs in jobs:
                yield cflash(e_already_uploaded, "error")
                if STRICT_NEW_IMAGES:
                    yield cflash(e_unnaceptable, "error")
                    break
                continue

            if current_app.extensions[PAGE_CACHE].has(hs):
                yield cflash(e_already_have, "error")
                if STRICT_NEW_IMAGES:
                    yield cflash(e_unnaceptable, "error")
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
                yield cflash(f'Failed OCR of "{name}":' + result["error"], "error")
            else:
                yield cflash(f'Finished OCR of "{name}" successfully', "success")
                current_app.extensions[PAGE_CACHE].set(hs, result)

        if futures:
            yield cflash(f'Finished OCR of all {len(futures)} files', "success")
        else:
            yield cflash('No files were processed', "warning")

    if request.args.get('stream'):
        return Response(function_results(), content_type='application/jsonlines')

    def dummy_gen():
        for _ in function_results():
            pass
        return json.dumps(get_flashed_messages(with_categories=True), ensure_ascii=False)
    return Response(dummy_gen(), content_type='application/json')


@v1.post('/make_html')
def make_html():
    if not (
        request.is_json and
        "title" in request.json and valid_title(request.json["title"]) and
        "page_map" in request.json and
        valid_image_map(request.json["page_map"])
    ):
        return {"error": 'Only non-empty JSON objects accepted.\nSchema: {"title": "file_title", "page_map": [[img_path, img_hash], ...]}'}, 415

    title = request.json["title"].strip()
    page_map = tuple(
        zip(
            map(lambda img_tpl: img_tpl[0].strip(), request.json["page_map"]),
            current_app.extensions[PAGE_CACHE].get_many(
                *map(lambda img_tpl: img_tpl[1].lower(), request.json["page_map"])),
        )
    )

    if not all(page_map):
        return {"error": "Asked for page not in cache"}, 400

    try:
        og = overlay_generator()
        page_htmls = [
            og.get_page_html(image_result, PurePath(image_path))
            for image_path, image_result in page_map
        ]
        return og.get_index_html(page_htmls, f'{title} | mokuro', True, False)

    except Exception as e:
        return {"error": str(e)}, 400


def valid_hash_list(hashes):
    return (
        isinstance(hashes, list) and
        all(hashes) and
        all(map(lambda hs: isinstance(hs, str), hashes)) and
        all(map(lambda hs: hash_reg.fullmatch(hs.lower()), hashes))
    )


def valid_title(title):
    return isinstance(title, str) and title.strip()


def valid_image_map(img_map):
    return (
        img_map and
        isinstance(img_map, list) and
        all(map(lambda tp: isinstance(tp, list), img_map)) and
        all(map(lambda tp: isinstance(tp[0], str) and tp[0].strip(), img_map)) and
        valid_hash_list(list(map(lambda tp: tp[1], img_map)))
    )


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
