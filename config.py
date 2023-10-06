class Config(object):
    OCR_CACHE_TYPE = "app.db.SqliteCache"
    OCR_CACHE_PATH = "./ocr_results.sqlite3"
    OCR_CACHE_MAX_SIZE = 100_000_000  # 100MB
    OCR_CACHE_THRESHOLD = 0
    OCR_CACHE_DEFAULT_TIMEOUT = 0
    OCR_CACHE_IGNORE_ERRORS = False
    STRICT_NEW_IMAGES = True
    MAX_IMAGE_SIZE = 5_000_000  # 5MB
    EXECUTOR_MAX_WORKERS = 1
    DEBUG = False
    SECRET_KEY = "- - - - - - - - - - - CHANGE THIS - - - - - - - - - - -"


class TestingConfig(Config):
    TESTING = True
    STRICT_NEW_IMAGES = False
    OCR_CACHE_TYPE = "SimpleCache"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    pass


class LocalConfig(Config):
    pass
