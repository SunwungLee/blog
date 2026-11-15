"""Support code for the n8n orchestration (docs/ORCHESTRATION_FOUNDATION.md)."""

import io
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

import helpers  # noqa: F401 - sets sys.path
from helpers import CID, request
from common.loader import load_script

alloc = load_script("id-allocator")


def _cli(main, argv, payload):
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    stdin = io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8")
    stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    with mock.patch("sys.stdin", stdin), mock.patch("sys.stdout", stdout):
        code = main(argv)
        stdout.flush()
        stdout.buffer.seek(0)
        return code, json.loads(stdout.buffer.read().decode("utf-8"))


METRICS = {"metrics": [{"platform": "naver", "metric_name": "views", "metric_value": 1, "measured_at": "2026-11-01"}]}


class HashOnlyTests(unittest.TestCase):
    def test_skill_hash_matches_real_run(self):
        import run_skill
        req = request("performance-analysis", METRICS, content_id=CID)
        code, real = _cli(run_skill.main, ["performance-analysis"], req)
        self.assertEqual(code, 0, real)
        code, pre = _cli(run_skill.main, ["performance-analysis", "--hash-only"], req)
        self.assertEqual(code, 0, pre)
        self.assertEqual(pre["output"]["input_hash"], real["usage"]["input_hash"])
        self.assertEqual(pre["run_id"], "run-1")
        self.assertEqual(pre["module"], "performance-analysis")

    def test_script_hash_matches_real_run(self):
        import run_script
        req = request("html-converter", {"markdown": "## 제목"})
        _, real = _cli(run_script.main, ["html-converter"], req)
        code, pre = _cli(run_script.main, ["html-converter", "--hash-only"], req)
        self.assertEqual(code, 0, pre)
        self.assertEqual(pre["output"]["input_hash"], real["usage"]["input_hash"])

    def test_hash_only_rejects_invalid_envelope_without_running(self):
        import run_skill
        req = request("performance-analysis", METRICS, content_id="bad")
        code, body = _cli(run_skill.main, ["performance-analysis", "--hash-only"], req)
        self.assertEqual(code, 1)
        self.assertEqual(body["error"]["code"], "INVALID_INPUT")
        wrong = request("fact-checking", METRICS, content_id=CID)
        code, body = _cli(run_skill.main, ["performance-analysis", "--hash-only"], wrong)
        self.assertEqual(body["error"]["code"], "INVALID_INPUT")


class CliRobustnessTests(unittest.TestCase):
    def test_skill_load_failure_returns_envelope(self):
        import run_skill
        req = request("performance-analysis", METRICS, content_id=CID)
        with mock.patch("run_skill.load_skill", side_effect=SyntaxError("boom secret")):
            code, body = _cli(run_skill.main, ["performance-analysis"], req)
        self.assertEqual(code, 1)
        self.assertEqual(body["error"]["code"], "UNKNOWN_FAILURE")
        self.assertNotIn("secret", json.dumps(body))

    def test_script_load_failure_returns_envelope(self):
        import run_script
        req = request("html-converter", {"markdown": "## a"})
        with mock.patch("run_script.load_script", side_effect=ImportError("secret")):
            code, body = _cli(run_script.main, ["html-converter"], req)
        self.assertEqual(code, 1)
        self.assertEqual(body["error"]["code"], "UNKNOWN_FAILURE")
        self.assertNotIn("secret", json.dumps(body))


class IdAllocatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_sequential_and_per_kind_per_date(self):
        self.assertEqual(alloc.allocate("topic", "2026-11-12", 3, state_dir=self.state),
                         ["TOP-20261112-0001", "TOP-20261112-0002", "TOP-20261112-0003"])
        self.assertEqual(alloc.allocate("topic", "2026-11-12", 1, state_dir=self.state), ["TOP-20261112-0004"])
        self.assertEqual(alloc.allocate("content", "2026-11-12", 1, state_dir=self.state), ["CNT-20261112-0001"])
        self.assertEqual(alloc.allocate("topic", "2026-11-13", 1, state_dir=self.state), ["TOP-20261113-0001"])

    def test_floor_reconciles_with_existing_records(self):
        self.assertEqual(alloc.allocate("content", "2026-11-12", 1, floor=7, state_dir=self.state), ["CNT-20261112-0008"])
        # a lower floor never moves the counter back
        self.assertEqual(alloc.allocate("content", "2026-11-12", 1, floor=2, state_dir=self.state), ["CNT-20261112-0009"])

    def test_concurrent_allocations_are_unique(self):
        def one(_):
            return alloc.allocate("topic", "2026-11-12", 2, state_dir=self.state)

        with ThreadPoolExecutor(max_workers=8) as pool:
            ids = [i for batch in pool.map(one, range(40)) for i in batch]
        self.assertEqual(len(ids), 80)
        self.assertEqual(len(set(ids)), 80)
        self.assertEqual(max(ids), "TOP-20261112-0080")

    def test_invalid_inputs(self):
        from common.errors import SkillError
        for args in (("draft", "2026-11-12", 1), ("topic", "20261112", 1), ("topic", "2026-11-12", 0),
                     ("topic", "2026-11-12", 101)):
            with self.assertRaises(SkillError) as ctx:
                alloc.allocate(*args, state_dir=self.state)
            self.assertEqual(ctx.exception.code, "INVALID_INPUT")
        with self.assertRaises(SkillError) as ctx:
            alloc.allocate("topic", "2026-11-12", 2, floor=9998, state_dir=self.state)
        self.assertEqual(ctx.exception.code, "STORAGE_FAILURE")
        # an exhausted request must not consume sequence numbers
        self.assertEqual(alloc.allocate("topic", "2026-11-12", 1, floor=9998, state_dir=self.state), ["TOP-20261112-9999"])

    def test_corrupt_state_is_storage_failure(self):
        from common.errors import SkillError
        (self.state / alloc.STATE_FILE).write_text("{not json", encoding="utf-8")
        with self.assertRaises(SkillError) as ctx:
            alloc.allocate("topic", "2026-11-12", 1, state_dir=self.state)
        self.assertEqual(ctx.exception.code, "STORAGE_FAILURE")

    def test_via_run_script(self):
        import run_script
        req = request("id-allocator", {"kind": "content", "date": "2026-11-12", "count": 2, "floor": 4})
        with mock.patch.dict("os.environ", {alloc.STATE_ENV: str(self.state)}):
            code, body = _cli(run_script.main, ["id-allocator"], req)
        self.assertEqual(code, 0, body)
        self.assertEqual(body["output"]["ids"], ["CNT-20261112-0005", "CNT-20261112-0006"])


if __name__ == "__main__":
    unittest.main()
