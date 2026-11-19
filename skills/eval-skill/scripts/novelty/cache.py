import threading
from collections import Counter, defaultdict

from .textutil import now_iso, read_json, save_json


class Cache:
    def __init__(self, directory):
        self.directory = directory
        self.locks = defaultdict(threading.Lock)
        self.guard = threading.Lock()
        self.hits = Counter()

    def get(self, kind, key, compute):
        path = self.directory / kind / key[:2] / f"{key}.json"
        with self.guard:
            lock = self.locks[path]
        with lock:
            existing = read_json(path)
            if existing is not None:
                with self.guard:
                    self.hits[kind] += 1
                return existing["value"], True
            value = compute()
            save_json(path, {"value": value, "saved_at": now_iso()})
            return value, False
