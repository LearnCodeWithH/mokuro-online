class Config(object):
    CACHE_TYPE = "FileSystemCache"
    CACHE_DEFAULT_TIMEOUT = 0
    # 10k of 'mokuro jsons' using (the rare size of) 10k each, takes 100mb of space...
    CACHE_THRESHOLD = 30000
    CACHE_DIR = "./cache"


class DevelopmentConfig(Config):
    pass


class TestingConfig(Config):
    TESTING = True
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 0
    CACHE_THRESHOLD = 0
    CACHE_IGNORE_ERRORS = False


class ProductionConfig(Config):
    pass
