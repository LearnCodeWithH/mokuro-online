class Config(object):
    OCR_CACHE_TYPE = "FileSystemCache"
    OCR_CACHE_DEFAULT_TIMEOUT = 0
    # 10k of 'mokuro jsons' using (the rare size of) 10k each, takes 100mb of space...
    OCR_CACHE_THRESHOLD = 30000
    OCR_CACHE_DIR = "./cache"
    STRICT_NEW_IMAGES = True
    MAX_IMAGE_SIZE = 5_000_000  # 5MB
    EXECUTOR_MAX_WORKERS = 1


class TestingConfig(Config):
    TESTING = True
    STRICT_NEW_IMAGES = False
    OCR_CACHE_TYPE = "SimpleCache"
    OCR_CACHE_THRESHOLD = 0
    OCR_CACHE_IGNORE_ERRORS = False


class DevelopmentConfig(Config):
    OCR_CACHE_TYPE = "SimpleCache"
    OCR_CACHE_IGNORE_ERRORS = False


class ProductionConfig(Config):
    pass
