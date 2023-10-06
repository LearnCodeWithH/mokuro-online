import json
import re
import concurrent.futures
import threading
import tempfile
from functools import wraps
from pathlib import Path, PurePath
from hashlib import md5
from flask import request, Response, Blueprint, current_app, flash, get_flashed_messages, stream_with_context
from . import OCR_CACHE, overlay_generator, manga_page_ocr

v1 = Blueprint('v1', __name__, url_prefix='/v1')
site = Blueprint('site', __name__)
hash_reg = re.compile("[a-f0-9]{32}")


@site.get('/')
def index():
    return current_app.send_static_file('index.html')


@v1.post('/hash_check')
def hash_check():
    if not (request.is_json and valid_hash_list(request.json)):
        return {"error": "Only JSON arrays of MD5 hashes are accepted"}, 415

    hashes = dict.fromkeys(request.json)
    hashes_lower = tuple(map(str.lower, hashes))
    with current_app.queue_lock:
        queue = tuple(
            hs for hs, lhs in zip(hashes, hashes_lower)
            if lhs in current_app.queue
        )
        if hasattr(current_app.extensions[OCR_CACHE], "has_many"):
            in_cache = current_app.extensions[OCR_CACHE].has_many(
                *hashes_lower)
            new = tuple(
                hs for hs, lhs in zip(hashes, hashes_lower)
                if (lhs not in current_app.queue and lhs not in in_cache)
            )
        else:
            new = tuple(
                hs for hs, lhs in zip(hashes, hashes_lower)
                if (lhs not in current_app.queue and
                    not current_app.extensions[OCR_CACHE].has(lhs))
            )

    return {"new": new, "queue": queue}


@v1.post('/ocr')
def ocr():
    if not (request.is_json and valid_hash_list(request.json)):
        return {"error": "Only JSON arrays of MD5 hashes are accepted"}, 415

    hashes = tuple(hs for hs in dict.fromkeys(request.json))
    results = current_app.extensions[OCR_CACHE].get_many(
        *map(lambda hs: hs.lower(), hashes))

    ocr = {hs: rs for hs, rs in zip(hashes, results) if rs != None}
    new = tuple(hs for hs, rs in zip(hashes, results) if rs == None)

    return {"ocr": ocr, "new": new}


def flashes_or_jsonlstream():
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if request.args.get('stream'):
                return Response(func(*args, **kwargs), content_type='application/jsonlines')

            def dummy_gen():
                for _ in func(*args, **kwargs):
                    pass
                return json.dumps(get_flashed_messages(with_categories=True), ensure_ascii=False)

            return Response(dummy_gen(), content_type='application/json')
        return decorated_function
    return decorator


@v1.post('/new_pages')
@stream_with_context
@flashes_or_jsonlstream()
def new_pages():
    MAX_IMAGE_SIZE = current_app.config["MAX_IMAGE_SIZE"]
    STRICT_NEW_IMAGES = current_app.config["STRICT_NEW_IMAGES"]

    # TODO: improve flashing messages to include file name

    e_too_large = f"File size is too large. At most {MAX_IMAGE_SIZE} bytes are accepted"
    e_file_empty = "Empty file was uploaded"
    e_key_not_hash = "File form key is not a valid hash"
    e_hash_no_match = "File form hash given is not the same hash as the file"
    e_not_image = "Files need to be images"
    e_already_have = "We already have the page in cache"
    e_unnaceptable = "Ignoring new images because of unacceptable client error"

    def cflash(msg, cat):
        flash(msg, cat)
        return json.dumps([str(msg), str(cat)], ensure_ascii=False) + '\n'

    jobs = {}

    if not request.files:
        yield cflash("No files were uploaded", "error")

    try:
        for hs, file in request.files.items():
            hs = hs.lower()
            name = file.filename

            if not hash_reg.fullmatch(hs):
                yield cflash(e_key_not_hash, "error")
                continue

            with current_app.queue_lock:
                if hs in current_app.queue:
                    yield cflash(f'Already have file "{name}" in queue', "success")
                    jobs[hs] = current_app.queue[hs]
                    continue

            if current_app.extensions[OCR_CACHE].has(hs):
                yield cflash(f'Already have file "{name}" in cache', "success")
                continue

            if file.content_length and file.content_length > MAX_IMAGE_SIZE:
                yield cflash(e_too_large, "error")
                continue

            if file.mimetype and not file.mimetype.startswith("image/"):
                yield cflash(e_not_image, "error")
                continue

            blob = file.read()

            if not blob:
                yield cflash(e_file_empty, "error")
                continue

            if len(blob) > MAX_IMAGE_SIZE:
                yield cflash(e_too_large, "error")
                if STRICT_NEW_IMAGES:
                    yield cflash(e_unnaceptable, "error")
                    break
                continue

            if hs != md5(blob).hexdigest():
                yield cflash(e_hash_no_match, "error")
                if STRICT_NEW_IMAGES:
                    yield cflash(e_unnaceptable, "error")
                    break
                continue

            temp_file = tempfile.NamedTemporaryFile(prefix="mokuro_page_")
            temp_file.write(blob)
            jobs[hs] = (hs, name, temp_file)

            yield cflash(f'Uploaded file "{name}" successfully', "success")
    except Exception as e:
        yield cflash(f'Failed uploads: {e}', "error")
    finally:
        with current_app.queue_lock:
            futures = []
            for hs, job in jobs.items():
                if isinstance(job, tuple) and hs not in current_app.queue:
                    future = current_app.extensions["executor"].submit(
                        do_page_ocr, *job)
                    current_app.queue[hs] = future
                    futures.append(future)
                elif isinstance(job, tuple):
                    futures.append(current_app.queue[hs])
                else:
                    futures.append(job)
        current_app.logger.info(f'User uploaded "{len(futures)} files"')

    yield cflash('Awaiting OCR of files', "info")

    for future in concurrent.futures.as_completed(futures):
        hs, name, result = future.result()
        if "error" in result:
            yield cflash(f'Failed OCR of "{name}":' + result["error"], "error")
        else:
            yield cflash(f'Finished OCR of "{name}" successfully', "success")

    if futures:
        yield cflash(f'Finished OCR of all {len(futures)} files', "success")
    else:
        yield cflash('No files were processed', "warning")


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
            current_app.extensions[OCR_CACHE].get_many(
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
        current_app.logger.info(f'Starting OCR of "{name}"')
        result = manga_page_ocr(path)
        current_app.extensions[OCR_CACHE].set(hs, result)

        return hs, name, result
    except AttributeError:
        return hs, name, {"error": "Animation file, Corrupted file or Unsupported type"}
    except Exception as e:
        return hs, name, {"error": str(e)}
    finally:
        with current_app.queue_lock:
            del current_app.queue[hs]
        # either way, when temp_file is garbage collected, it will be deleted
        temp_file.close()
