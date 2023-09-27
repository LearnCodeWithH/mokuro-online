class Config(object):
    PAGE_CACHE_TYPE = "FileSystemCache"
    PAGE_CACHE_DEFAULT_TIMEOUT = 0
    # 10k of 'mokuro jsons' using (the rare size of) 10k each, takes 100mb of space...
    PAGE_CACHE_THRESHOLD = 30000
    PAGE_CACHE_DIR = "./cache"
    STRICT_HASHES = False
    STRICT_NEW_IMAGES = False
    MAX_IMAGE_SIZE = 5_000_000  # 5MB
    EXECUTOR_MAX_WORKERS = 1


class DevelopmentConfig(Config):
    STRICT_HASHES = True
    STRICT_NEW_IMAGES = False


class TestingConfig(Config):
    TESTING = True
    STRICT_HASHES = False
    STRICT_NEW_IMAGES = False
    PAGE_CACHE_TYPE = "SimpleCache"
    PAGE_CACHE_DEFAULT_TIMEOUT = 0
    PAGE_CACHE_THRESHOLD = 0
    PAGE_CACHE_IGNORE_ERRORS = False


class ProductionConfig(Config):
    STRICT_HASHES = True
    STRICT_NEW_IMAGES = True
