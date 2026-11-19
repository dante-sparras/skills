import queue
import statistics
import threading
import time
from collections import defaultdict

from .clis import CallError

PARSE_ERRORS = (ValueError, KeyError, TypeError)
MIN_HEDGE = 15.0


class Caller:
    def __init__(self, adapters, panel, hedge):
        self.adapters = adapters
        self.hedge = hedge
        self.slots = {cli: threading.Semaphore(panel.parallel(cli)) for cli in adapters}
        self.records = []
        self.durations = defaultdict(list)
        self.lock = threading.Lock()

    def call(self, seat, system, prompt, parse, kind, skill, attempts=3, repair=True, models=False):
        errors = []
        current = prompt
        for attempt in range(1, attempts + 1):
            queued = time.monotonic()
            with self.slots[seat.cli]:
                record = {"skill": skill, "kind": kind, "seat": seat.key, "attempt": attempt,
                          "queued_at": queued, "started_at": time.monotonic()}
                try:
                    reply = self.race(seat, system, current, kind, record)
                    record["models"] = list(reply.models)
                    value = parse(reply.text)
                    record["ok"] = True
                    self.remember(kind, seat, time.monotonic() - record["started_at"])
                    return (value, reply.models) if models else value
                except (CallError, *PARSE_ERRORS) as error:
                    record.update(ok=False, error=str(error)[:300])
                    errors.append(str(error))
                    if repair and isinstance(error, PARSE_ERRORS):
                        current = (f"{prompt}\n\nA previous reply to this request was rejected: {str(error)[:1500]}\n"
                                   "Reply again in full and fix that.")
                finally:
                    record["ended_at"] = time.monotonic()
                    with self.lock:
                        self.records.append(record)
        raise CallError(f"{kind} on {seat.key} failed {attempts} times: {errors[-1][:300]}")

    def remember(self, kind, seat, seconds):
        with self.lock:
            self.durations[(kind.split("-")[0], seat.key)].append(seconds)

    def hedge_after(self, kind, seat):
        with self.lock:
            seen = list(self.durations[(kind.split("-")[0], seat.key)])
        if len(seen) < 3:
            return self.hedge
        return min(self.hedge, max(MIN_HEDGE, 2 * statistics.median(seen)))

    def race(self, seat, system, prompt, kind, record):
        adapter = self.adapters[seat.cli]
        results = queue.Queue()
        cancels = []

        def attempt(cancel, extra_slot):
            try:
                results.put((True, adapter.ask(seat, system, prompt, cancel)))
            except Exception as error:
                results.put((False, error if isinstance(error, CallError) else CallError(repr(error))))
            finally:
                if extra_slot:
                    self.slots[seat.cli].release()

        def launch(extra_slot):
            cancel = threading.Event()
            cancels.append(cancel)
            threading.Thread(target=attempt, args=(cancel, extra_slot), daemon=True).start()

        launch(False)
        running = 1
        try:
            try:
                ok, value = results.get(timeout=self.hedge_after(kind, seat))
            except queue.Empty:
                if self.slots[seat.cli].acquire(blocking=False):
                    launch(True)
                    running += 1
                    record["hedged"] = True
                ok, value = results.get()
            running -= 1
            while not ok and running:
                ok, value = results.get()
                running -= 1
            if not ok:
                raise value
            return value
        finally:
            for cancel in cancels:
                cancel.set()
