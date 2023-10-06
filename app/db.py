from flask import g, current_app
from flask_caching.backends.base import BaseCache
from contextlib import contextmanager
from time import time
from functools import wraps
import sqlite3
import logging
import pickle


class SqliteCache(BaseCache):
    _CREATE_SQL = (
        'CREATE TABLE IF NOT EXISTS entries '
        '( key TEXT PRIMARY KEY, val BLOB, exp FLOAT, updated FLOAT )'
    )
    _CREATE_INDEX = 'CREATE INDEX IF NOT EXISTS keyname_index ON entries (key)'
    _HAS_SQL = 'SELECT      exp FROM entries WHERE key = ?'
    _GET_SQL = 'SELECT val, exp FROM entries WHERE key = ?'
    _HAS_MANY_SQL = 'SELECT key,      exp FROM entries WHERE key IN ({})'
    _GET_MANY_SQL = 'SELECT key, val, exp FROM entries WHERE key IN ({})'
    _DEL_SQL = 'DELETE FROM entries WHERE key = ?'
    _DEL_MANY_SQL = 'DELETE FROM entries WHERE key IN ({})'
    _SET_SQL = 'INSERT OR REPLACE INTO entries (key, val, exp, updated) VALUES (?, ?, ?, ?)'
    _SET_MANY_SQL = 'INSERT OR REPLACE INTO entries (key, val, exp, updated) VALUES {}'
    _ADD_SQL = 'INSERT INTO entries (key, val, exp, updated) VALUES (?, ?, ?, ?)'
    _CLEAR_SQL = 'DELETE FROM entries'
    _CLEAR_EXPIRED_SQL = 'DELETE FROM entries WHERE exp > 0 AND exp <= ?'
    _TOTAL_SIZE_SQL = 'SELECT page_count * page_size AS total_bytes FROM pragma_page_count, pragma_page_size'

    _COUNT_ENTRIES_SQL = 'SELECT COUNT(*) FROM entries'

    def __init__(self, path, default_timeout=0, threshold=0, max_size=0, logger=None, ignore_errors=True):
        BaseCache.__init__(self, default_timeout)
        self.path = path  # path of the database file
        self.threshold = threshold or 0  # maximum number of entries
        self.max_size = max_size or 0  # max size of the sqlite file in bytes
        self.mem_conn = None
        self.ignore_errors = ignore_errors
        self.logger = logger or logging.getLogger(__name__)

        with self.get_connection() as conn:
            self.logger.debug(f'Connected to "{self.path}"')
            conn.execute(self._CREATE_SQL)
            conn.execute(self._CREATE_INDEX)
            conn.commit()
            conn.execute('VACUUM')

    @classmethod
    def factory(cls, app, config, args, kwargs):
        kwargs.update(dict(
            logger=app.logger,
            path=config.get("CACHE_PATH"),
            default_timeout=config.get("CACHE_DEFAULT_TIMEOUT", None),
            threshold=config.get("CACHE_THRESHOLD", None),
            # dir=config.get("CACHE_DIR", None),
            max_size=config.get("CACHE_MAX_SIZE", None),
            ignore_errors=config.get("CACHE_IGNORE_ERRORS", False),
        ))
        return cls(*args, **kwargs)

    def log_sqlite_errors(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except sqlite3.Error as e:
                self.logger.error(
                    f"SQLite error in '{func.__name__}()': {str(e)}")
                if not self.ignore_errors:
                    raise e
            except Exception as e:
                self.logger.error(
                    f"Cache error in '{func.__name__}()': {str(e)}")
                if not self.ignore_errors:
                    raise e
        return wrapper

    @contextmanager
    @log_sqlite_errors
    def get_connection(self):
        if self.path == ":memory:":
            if not self.mem_conn:
                self.logger.warning(
                    "Using in-memory sqlite database. This WILL crash on multi-threaded environment.")
                self.mem_conn = sqlite3.connect(self.path, timeout=60)
                self.mem_conn.row_factory = sqlite3.Row
            with self.mem_conn:
                yield self.mem_conn
            return

        conn = None
        try:
            conn = sqlite3.connect(self.path, timeout=60)
            conn.row_factory = sqlite3.Row
            with conn:
                yield conn
        finally:
            if conn:
                conn.close()

    @log_sqlite_errors
    def has(self, key):
        with self.get_connection() as conn:
            cur = conn.execute(self._HAS_SQL, (key,))
            row = cur.fetchone()
            if row:
                exp = row[0]
                return exp == 0 or exp > time()
            return False

    @log_sqlite_errors
    def has_many(self, *keys):
        with self.get_connection() as conn:
            cur = conn.execute(
                self._HAS_MANY_SQL.format(','.join('?' * len(keys))), keys)
            results = []
            for row in cur.fetchall():
                key, exp = row
                if exp == 0 or exp > time():
                    results.append(key)
            return results

    @log_sqlite_errors
    def get(self, key):
        with self.get_connection() as conn:
            cur = conn.execute(self._GET_SQL, (key,))
            row = cur.fetchone()
            if row:
                value, exp = row
                if exp == 0 or exp > time():
                    return pickle.loads(value)

    @log_sqlite_errors
    def get_many(self, *keys):
        with self.get_connection() as conn:
            cur = conn.execute(
                self._GET_MANY_SQL.format(','.join('?' * len(keys))), keys)
            results = {}
            for row in cur.fetchall():
                key, value, exp = row
                if exp == 0 or exp > time():
                    results[key] = pickle.loads(value)
            return [results.get(key) for key in keys]

    @log_sqlite_errors
    def delete(self, key):
        with self.get_connection() as conn:
            cur = conn.execute(self._DEL_SQL, (key,))
            self.cleanup_full(conn)
            return cur.rowcount > 0

    @log_sqlite_errors
    def delete_many(self, *keys):
        exists = self.has_many(*keys)
        with self.get_connection() as conn:
            cur = conn.execute(
                self._DEL_MANY_SQL.format(', '.join('?'*len(exists))), exists)
            self.cleanup_full(conn)
            return exists

    @log_sqlite_errors
    def clear(self):
        with self.get_connection() as conn:
            conn.execute(self._CLEAR_SQL)
            conn.commit()
            conn.execute('VACUUM')
            return True

    @log_sqlite_errors
    def add(self, key, value, timeout=None):
        timeout = self._normalize_timeout(timeout)
        exp = 0 if timeout == 0 else time() + timeout
        value = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        updated = time()
        with self.get_connection() as conn:
            try:
                cur = conn.execute(self._ADD_SQL, (key, value, exp, updated))
                self.cleanup_full(conn)
                return cur.rowcount > 0
            except sqlite3.IntegrityError:
                return False

    @log_sqlite_errors
    def set(self, key, value, timeout=None):
        timeout = self._normalize_timeout(timeout)
        exp = 0 if timeout == 0 else time() + timeout
        value = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        updated = time()
        with self.get_connection() as conn:
            cur = conn.execute(self._SET_SQL, (key, value, exp, updated))
            self.cleanup_full(conn)
            return cur.rowcount > 0

    @log_sqlite_errors
    def set_many(self, mapping, timeout=None):
        timeout = self._normalize_timeout(timeout)
        exp = 0 if timeout == 0 else time() + timeout
        sql = self._SET_MANY_SQL.format(
            ','.join(('(?, ?, ?, ?)',) * len(mapping)))
        args = [
            item
            for key, value in mapping.items()
            for item in (
                key,
                pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL),
                exp,
                time()
            )
        ]
        with self.get_connection() as conn:
            conn.execute(sql, args)
            self.cleanup_full(conn)
            return list(mapping.keys())

    @log_sqlite_errors
    def cleanup_full(self, conn=None):
        if conn is None:
            with self.get_connection() as conn:
                return self.cleanup_full(conn)
        self.cleanup_expired(conn)
        self.cleanup_threshold(conn)
        self.cleanup_max_size(conn)

    @log_sqlite_errors
    def cleanup_expired(self, conn=None):
        if conn is None:
            with self.get_connection() as conn:
                conn.execute(self._CLEAR_EXPIRED_SQL, (time(),))
        else:
            conn.execute(self._CLEAR_EXPIRED_SQL, (time(),))

    @log_sqlite_errors
    def cleanup_threshold(self, conn=None):
        if not self.threshold:
            return True

        if conn is None:
            with self.get_connection() as conn:
                return self.cleanup_threshold(conn)

        current_count = conn.execute(self._COUNT_ENTRIES_SQL).fetchone()[0]

        if current_count <= self.threshold:
            return True  # Nothing to clear

        excess_count = max(0, current_count - self.threshold)

        # Get the oldest entries with exp > 0
        cur = conn.execute(
            'SELECT key FROM entries ORDER BY updated ASC LIMIT ?',
            (excess_count,),
        )
        rows = cur.fetchall()

        # Delete all the identified entries in a single query
        keys = tuple(row[0] for row in rows)
        conn.execute(self._DEL_MANY_SQL.format(','.join('?'*len(keys))), keys)

        return True

    @log_sqlite_errors
    def cleanup_max_size(self, conn=None):
        if not self.max_size:
            return True

        if conn is None:
            with self.get_connection() as conn:
                return self.cleanup_max_size(conn)

        total_size = conn.execute(self._TOTAL_SIZE_SQL).fetchone()[0]

        while total_size > self.max_size:
            # Get the 10 oldest entries with exp > 0
            cur = conn.execute(
                'SELECT key, length(val) FROM entries ORDER BY updated ASC LIMIT 10'
            )
            entries = cur.fetchall()

            if not entries:
                break

            for key, value_size in entries:
                conn.execute(self._DEL_SQL, (key,))
                total_size -= value_size
                if not total_size > self.max_size:
                    break
        return True
