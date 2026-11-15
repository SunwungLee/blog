"""Tests for the decisions that replaced the deferred review items (Phase 0 20.13)."""

import json
import unittest

import helpers  # noqa: F401 - sets sys.path
from helpers import CID, assert_error, fake_llm, fake_search, request
from common import usage
from common.loader import load_skill
from common.sources import run_search

pa = load_skill("platform-adaptation")
pf = load_skill("performance-analysis")
td = load_skill("topic-discovery")

ARTICLE = ("# 제목\n\n## 방법\n\n월 10만원을 받습니다. 자세한 내용은 https://www.fss.or.kr/a 에서 확인하세요.\n\n"
           "## 준비물\n\n신분증이 필요합니다.")
IMAGES = [{"image_id": "img1", "status": "RIGHTS_CONFIRMED", "url": "https://img.example.com/1.png",
           "alt_text": "설명", "slot_heading": "준비물"}]
AI_BODY = {"title": "새 제목", "meta_description": "메타", "summary": "말투 변경",
           "body_markdown": "## 방법\n\n한 달에 10만원이 들어와요. 공식 안내는 https://www.fss.or.kr/a 에 있어요.\n\n## 준비물\n\n신분증을 챙기세요."}


def m(platform, name, value, at):
    return {"platform": platform, "metric_name": name, "metric_value": value, "measured_at": at}


def frun(inp, llm=None):
    return pf.run(request("performance-analysis", inp, content_id=CID), llm=llm)


def prun(llm, **over):
    inp = {"article_markdown": ARTICLE, "title": "제목", "platform": "blogspot", "content_type": "guide", "images": IMAGES}
    inp.update(over)
    return pa.run(request("platform-adaptation", inp, content_id=CID), llm=llm)


class UsageTests(unittest.TestCase):
    def test_usage_counts_and_tokens(self):
        payload = json.dumps({"suggestions": []})
        llm = lambda role, system, prompt: {"text": payload, "usage": {"input_tokens": 120, "output_tokens": 30}}
        resp = frun({"metrics": [m("naver", "views", 10, "2026-11-01")]}, llm)
        self.assertEqual(resp["usage"]["llm_calls"], 1)
        self.assertEqual(resp["usage"]["input_tokens"], 120)
        self.assertEqual(resp["usage"]["output_tokens"], 30)
        self.assertEqual(len(resp["usage"]["input_hash"]), 64)

    def test_tokens_unknown_when_adapter_omits_them(self):
        resp = frun({"metrics": [m("naver", "views", 10, "2026-11-01")]}, fake_llm({"suggestions": []}))
        self.assertEqual(resp["usage"]["llm_calls"], 1)
        self.assertIsNone(resp["usage"]["input_tokens"])

    def test_input_hash_is_deterministic_and_failure_has_usage(self):
        a = frun({"metrics": [m("naver", "views", 10, "2026-11-01")]})["usage"]["input_hash"]
        b = frun({"metrics": [m("naver", "views", 10, "2026-11-01")]})["usage"]["input_hash"]
        c = frun({"metrics": [m("naver", "views", 11, "2026-11-01")]})["usage"]["input_hash"]
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        failed = frun({"metrics": []})
        self.assertIn("error", failed)
        self.assertEqual(failed["usage"]["llm_calls"], 0)

    def test_search_calls_counted(self):
        meter, token = usage.start()
        try:
            run_search(fake_search([]), "q")
            run_search(fake_search([]), "q2")
        finally:
            usage.stop(token)
        self.assertEqual(meter.search_calls, 2)

    def test_validator_accepts_usage(self):
        from common.loader import load_script
        dv = load_script("data-validator")
        resp = frun({"metrics": [m("naver", "views", 10, "2026-11-01")]})
        self.assertEqual(dv.validate_envelope(resp), [])


class LocaleTests(unittest.TestCase):
    def test_only_ko_kr(self):
        inp = {"editorial_context": "육아 블로그", "active_content_types": ["guide"], "locale": "en-US"}
        resp = td.run(request("topic-discovery", inp, discovery_run_id="run-x"), llm=fake_llm({}), search=fake_search([]))
        assert_error(self, resp, "INVALID_INPUT")


class PublishingLinkTests(unittest.TestCase):
    PUB = [{"publishing_id": "p-naver", "platform": "naver", "human_published_at": "2026-11-01T09:00:00+09:00"},
           {"publishing_id": "p-old", "platform": "blogspot", "human_published_at": None}]

    def test_days_and_warnings(self):
        rows = [m("naver", "views", 5, "2026-10-31T09:00:00+09:00"), m("naver", "views", 1000, "2026-11-02T09:00:00+09:00"),
                m("naver", "views", 400, "2026-11-11T09:00:00+09:00"), m("blogspot", "views", 50, "2026-11-11T09:00:00+09:00")]
        out = frun({"metrics": rows, "publishing": self.PUB})["output"]
        views = next(s for s in out["summary"] if s["platform"] == "naver")
        self.assertEqual(views["samples"], 2)  # pre-publication row dropped
        self.assertEqual(views["days_since_publish"], 10)
        self.assertEqual(views["publishing_id"], "p-naver")
        codes = [w["code"] for w in out["warnings"]]
        self.assertIn("MEASURED_BEFORE_PUBLISH", codes)
        self.assertIn("METRICS_WITHOUT_PUBLISHING", codes)
        self.assertIn("decline", {s["type"] for s in out["suggestions"]})
        self.assertEqual([p["publishing_id"] for p in out["publishing"]], ["p-naver"])

    def test_early_decline_not_suggested(self):
        rows = [m("naver", "views", 1000, "2026-11-02T09:00:00+09:00"), m("naver", "views", 400, "2026-11-04T09:00:00+09:00")]
        out = frun({"metrics": rows, "publishing": self.PUB[:1]})["output"]
        self.assertNotIn("decline", {s["type"] for s in out["suggestions"]})

    def test_missing_publishing_and_no_metrics(self):
        out = frun({"metrics": [m("naver", "views", 10, "2026-11-01")]})["output"]
        self.assertIn("PUBLISHING_REFS_MISSING", [w["code"] for w in out["warnings"]])
        pub = self.PUB[:1] + [{"publishing_id": "p-b", "platform": "blogspot", "human_published_at": "2026-11-01T09:00:00+09:00"}]
        out = frun({"metrics": [m("naver", "views", 10, "2026-11-05T09:00:00+09:00")], "publishing": pub})["output"]
        self.assertIn("NO_METRICS_FOR_PLATFORM", [w["code"] for w in out["warnings"]])

    def test_publishing_validation(self):
        rows = [m("naver", "views", 10, "2026-11-05")]
        assert_error(self, frun({"metrics": rows, "publishing": {}}), "INVALID_INPUT")
        assert_error(self, frun({"metrics": rows, "publishing": [{"platform": "naver"}]}), "INVALID_INPUT")
        assert_error(self, frun({"metrics": rows, "publishing": [{"publishing_id": "p", "platform": "naver", "human_published_at": "어제"}]}), "INVALID_INPUT")
        only_early = [m("naver", "views", 10, "2026-10-01")]
        assert_error(self, frun({"metrics": only_early, "publishing": self.PUB[:1]}), "INVALID_INPUT")


class ScriptFirstAdaptationTests(unittest.TestCase):
    def test_blogspot_converted_without_ai(self):
        llm = fake_llm(AI_BODY)
        out = prun(llm, meta_description="요약")["output"]
        self.assertEqual(llm.calls, [])
        self.assertEqual(out["adaptation_method"], "script")
        self.assertEqual(out["meta_description"], "요약")
        html = out["artifact"]["content"]
        self.assertNotIn("<h1>", html)
        self.assertIn("<h2>준비물</h2>", html)
        self.assertLess(html.index("<h2>준비물</h2>"), html.index('<img src="https://img.example.com/1.png"'))

    def test_falls_back_to_ai_when_too_similar_to_other_platform(self):
        llm = fake_llm(AI_BODY)
        out = prun(llm, other_platform_output=ARTICLE)["output"]
        self.assertEqual(out["adaptation_method"], "ai")
        self.assertEqual(len(llm.calls), 1)

    def test_naver_and_forced_ai_use_model(self):
        for over in ({"platform": "naver"}, {"adaptation_mode": "ai"}):
            llm = fake_llm(AI_BODY)
            out = prun(llm, **over)["output"]
            self.assertEqual(out["adaptation_method"], "ai")
            self.assertEqual(len(llm.calls), 1)

    def test_unplaced_image_and_invalid_mode(self):
        images = [dict(IMAGES[0], slot_heading="없는 소제목")]
        out = prun(fake_llm(AI_BODY), images=images)["output"]
        self.assertIn("IMAGE_NOT_PLACED", [w["code"] for w in out["warnings"]])
        assert_error(self, prun(fake_llm(AI_BODY), adaptation_mode="fast"), "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
