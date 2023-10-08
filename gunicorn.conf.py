import multiprocessing

bind = "127.0.0.1:8000"
threads = multiprocessing.cpu_count() + 1
wsgi_app = "app:create_app('local')"
