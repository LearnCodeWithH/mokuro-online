class Config(object):
    CACHE_TYPE = "FileSystemCache"
    CACHE_DEFAULT_TIMEOUT = 0
    # 10k of 'mokuro jsons' using (the rare size of) 10k each, takes 100mb of space...
    CACHE_THRESHOLD = 30000
    CACHE_DIR = "./cache"
    STRICT_HASHES = False
    STRICT_NEW_IMAGES = False
    MAX_IMAGE_SIZE = 5_000_000  # 5MB


class DevelopmentConfig(Config):
    STRICT_HASHES = True
    STRICT_NEW_IMAGES = False


class TestingConfig(Config):
    TESTING = True
    STRICT_HASHES = False
    STRICT_NEW_IMAGES = False
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 0
    CACHE_THRESHOLD = 0
    CACHE_IGNORE_ERRORS = False


class ProductionConfig(Config):
    STRICT_HASHES = True
    STRICT_NEW_IMAGES = True
