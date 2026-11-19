from .base import Adapter, CallError, Reply
from .claude import Claude
from .codex import Codex
from .grok import Grok
from .opencode import Opencode

ADAPTERS = {adapter.name: adapter for adapter in (Claude, Codex, Grok, Opencode)}


def connect(panel, timeout, adapters=None):
    registry = adapters or ADAPTERS
    connected, notes = {}, []
    for cli in panel.clis:
        adapter = registry[cli](timeout)
        notes.append(adapter.check_signin([seat for seat in panel.seats() if seat.cli == cli]))
        connected[cli] = adapter
    return connected, notes


__all__ = ["ADAPTERS", "Adapter", "CallError", "Reply", "connect"]
