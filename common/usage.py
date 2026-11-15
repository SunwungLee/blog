"""Per-call usage metering reported in the response envelope (`usage`).

An injected `llm` may return either the response text, or an object
`{"text": str, "usage": {"input_tokens": int, "output_tokens": int}}`.
Token counts are summed only when the adapter reports them; cost is computed
by the workflow from these counts and the current price table, not here.
"""

import contextvars

_current = contextvars.ContextVar("skill_usage", default=None)


class Meter:
    def __init__(self):
        self.llm_calls = 0
        self.search_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.tokens_reported = True

    def to_dict(self, input_hash=None):
        out = {"llm_calls": self.llm_calls, "search_calls": self.search_calls}
        if self.llm_calls:
            out["input_tokens"] = self.input_tokens if self.tokens_reported else None
            out["output_tokens"] = self.output_tokens if self.tokens_reported else None
        if input_hash:
            out["input_hash"] = input_hash
        return out


def start():
    meter = Meter()
    return meter, _current.set(meter)


def stop(token):
    _current.reset(token)


def _count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def llm_text(response):
    """Record one model call and return its text."""
    meter = _current.get()
    text, used = response, None
    if isinstance(response, dict) and "text" in response:
        text, used = response.get("text"), response.get("usage")
    if meter is not None:
        meter.llm_calls += 1
        tin = _count(used.get("input_tokens")) if isinstance(used, dict) else None
        tout = _count(used.get("output_tokens")) if isinstance(used, dict) else None
        if tin is None or tout is None:
            meter.tokens_reported = False
        else:
            meter.input_tokens += tin
            meter.output_tokens += tout
    return text


def search_call():
    meter = _current.get()
    if meter is not None:
        meter.search_calls += 1
