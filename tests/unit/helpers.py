import json
import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

NOW = datetime(2026, 11, 12, 15, 0, 0, tzinfo=timezone(timedelta(hours=9)))
TODAY = date(2026, 11, 12)
CID = "CNT-20261112-0001"
TID = "TOP-20261112-0001"


def request(module, inp, **refs):
    return {"schema_version": "1.0", "run_id": "run-1", "module": module, "refs": refs, "input": inp}


def fake_llm(*responses):
    """Return an llm callable that yields the given responses in order (dict -> JSON)."""
    queue = list(responses)
    calls = []

    def llm(role, system, prompt):
        calls.append((role, prompt))
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        return item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)

    llm.calls = calls
    return llm


def fake_search(results):
    calls = []

    def search(query, max_results):
        calls.append(query)
        return results

    search.calls = calls
    return search


def assert_error(test, response, code):
    test.assertIn("error", response, response)
    test.assertEqual(response["error"]["code"], code)
