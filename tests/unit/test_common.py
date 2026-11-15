import unittest

import helpers  # noqa: F401
from common import ids, privacy
from common.envelope import execute
from common.errors import SkillError
from common.llm import call_json, extract_json, run_with_quality
from common.loader import load_script
from common.sources import is_official, normalize_results
from common.util import similar
from datetime import date


class CommonTests(unittest.TestCase):
    def test_ids(self):
        self.assertEqual(ids.topic_id(date(2026, 11, 12), 1), "TOP-20261112-0001")
        self.assertEqual(ids.file_name("CNT-20261112-0001", "master", 1, "md"), "CNT-20261112-0001_master_v001.md")
        self.assertEqual(ids.drive_path("CNT-20261112-0001", "naver"), "content/CNT-20261112-0001/publishing/naver")
        with self.assertRaises(ValueError):
            ids.file_name("bad", "master", 1, "md")

    def test_privacy(self):
        self.assertIn("phone", privacy.find_pii("연락처 010-1234-5678"))
        self.assertIn("email", privacy.find_pii("a@b.com"))
        self.assertIn("blocked_term", privacy.find_pii("김철수 이야기", ["김철수"]))
        self.assertEqual(privacy.find_pii("아기 이유식 만들기"), [])

    def test_extract_json_handles_fences(self):
        self.assertEqual(extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        with self.assertRaises(ValueError):
            extract_json("no json")

    def test_call_json_repairs_twice_then_fails(self):
        calls = []

        def llm(role, system, prompt):
            calls.append(prompt)
            return "not json"

        with self.assertRaises(SkillError) as ctx:
            call_json(llm, "lightweight", "s", "p")
        self.assertEqual(ctx.exception.code, "INVALID_JSON")
        self.assertEqual(len(calls), 3)  # initial + 2 repairs

    def test_call_json_without_provider(self):
        with self.assertRaises(SkillError) as ctx:
            call_json(None, "lightweight", "s", "p")
        self.assertEqual(ctx.exception.code, "AUTH_OR_PERMISSION")

    def test_run_with_quality_limits_reruns(self):
        n = []
        with self.assertRaises(SkillError) as ctx:
            run_with_quality(lambda p: n.append(1), lambda r: ["bad"])
        self.assertEqual(ctx.exception.code, "QUALITY_BELOW_THRESHOLD")
        self.assertEqual(len(n), 3)

    def test_envelope_validation_and_unknown_failure(self):
        bad = execute({"schema_version": "2"}, "m", lambda i, r: {})
        self.assertEqual(bad["error"]["code"], "INVALID_INPUT")

        def boom(i, r):
            raise RuntimeError("secret-key-123")

        resp = execute(helpers.request("m", {}), "m", boom)
        self.assertEqual(resp["error"]["code"], "UNKNOWN_FAILURE")
        self.assertNotIn("secret", str(resp))

    def test_sources(self):
        self.assertTrue(is_official("https://www.fss.or.kr/a"))
        self.assertTrue(is_official("https://www.moef.go.kr/a"))
        self.assertFalse(is_official("https://blog.example.com"))
        res = normalize_results([{"title": "a", "url": "https://x.com/1"}, {"title": "a", "url": "https://x.com/1/"},
                                 {"title": "b", "url": "javascript:alert(1)"}, {"title": "", "url": "https://y.com"}])
        self.assertEqual(len(res), 1)

    def test_similar(self):
        self.assertTrue(similar("아기 이유식 시작 시기 총정리", "이유식 시작 시기"))
        self.assertFalse(similar("아기 이유식", "자동차 보험 비교"))

    def test_data_validator(self):
        dv = load_script("data-validator")
        self.assertEqual(dv.validate_envelope(helpers.request("m", {}, content_id="CNT-20261112-0001")), [])
        self.assertTrue(dv.validate_envelope(helpers.request("m", {}, content_id="bad")))
        self.assertTrue(dv.validate_envelope({"schema_version": "1.0", "run_id": "r", "module": "m", "refs": {}}))
        schema = {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer", "minimum": 1}}}
        self.assertEqual(dv.validate({"a": 2}, schema), [])
        self.assertTrue(dv.validate({"a": True}, schema))


if __name__ == "__main__":
    unittest.main()
