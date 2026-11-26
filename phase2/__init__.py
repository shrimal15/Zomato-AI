"""Phase 2 preferences: validate a request before any restaurant filter runs."""

from phase2.collect import accept_json, collect, preference_errors
from phase2.options import PreferenceOptions, options_for

__all__ = [
    "PreferenceOptions",
    "accept_json",
    "collect",
    "options_for",
    "preference_errors",
]
