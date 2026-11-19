from .clis import CallError
from .prompts import PROBE_PROMPT, PROBE_SYSTEM, parse_ok


class Identities:
    def __init__(self, caller, seats, pool):
        self.futures = {seat.key: pool.submit(self.probe, caller, seat) for seat in dict.fromkeys(seats)}

    @staticmethod
    def probe(caller, seat):
        _, models = caller.call(seat, PROBE_SYSTEM, PROBE_PROMPT, parse_ok, "probe", "-", models=True)
        return "+".join(models) or seat.model

    def model(self, seat):
        try:
            return self.futures[seat.key].result()
        except CallError as error:
            raise CallError(f"{seat.key} did not answer the model probe: {error}")

    def of(self, seat):
        return f"{seat.key}@{self.model(seat)}"

    def resolved(self):
        result = {}
        for key, future in self.futures.items():
            try:
                result[key] = future.result()
            except CallError as error:
                result[key] = f"unresolved: {error}"[:200]
        return result
