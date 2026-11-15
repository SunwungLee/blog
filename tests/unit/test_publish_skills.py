import io
import json
import unittest
from contextlib import redirect_stdout
from unittest import mock

import helpers
from helpers import CID, NOW, assert_error, fake_llm, request
from common.loader import load_skill

ip = load_skill("image-preparation")
pa = load_skill("platform-adaptation")
pf = load_skill("performance-analysis")

ARTICLE = "# 제목\n\n## 준비물\n\n내용\n\n## 방법\n\n내용"


def img(**over):
    d = {"slot_heading": "준비물", "purpose": "준비물 보여주기", "alt_text": "이유식 준비물이 놓인 식탁", "caption": "", "source_type": "own", "guide": "식탁 위 준비물 촬영"}
    d.update(over)
    return d


def irun(llm, **over):
    inp = {"article_markdown": ARTICLE}
    inp.update(over)
    return ip.run(request("image-preparation", inp, content_id=CID), llm=llm, now=NOW)


class ImagePreparationTests(unittest.TestCase):
    def test_plan_and_rights_gate(self):
        assets = [{"image_id": "img-1", "source_type": "own", "drive_file_id": "f1", "rights_note": "직접 촬영", "rights_checked_at": "2026-11-12T10:00:00+09:00", "width": 2400, "height": 1200},
                  {"image_id": "img-2", "source_type": "licensed", "drive_file_id": "f2", "rights_note": ""}]
        out = irun(fake_llm({"images": [img()]}), assets=assets)["output"]
        self.assertEqual(out["image_plan"][0]["status"], "PLANNED")
        self.assertEqual(len(out["usable_image_ids"]), 1)
        self.assertEqual(len(out["unusable_image_ids"]), 1)
        self.assertEqual(out["assets"][0]["resize_to"], {"width": 1200, "height": 600})
        self.assertIn("RIGHTS_UNCONFIRMED", [w["code"] for w in out["warnings"]])

    def test_privacy_and_limits(self):
        imgs = [img(guide="아이 얼굴 정면 촬영"), img(alt_text=""), img(source_type="stock"), img(), img(slot_heading="방법"), img(slot_heading="방법2")]
        out = irun(fake_llm({"images": imgs}), constraints={"max_images": 2})["output"]
        self.assertEqual(len(out["image_plan"]), 2)
        codes = [w["code"] for w in out["warnings"]]
        self.assertIn("IMAGE_DROPPED_PRIVACY", codes)
        self.assertEqual(codes.count("IMAGE_DROPPED"), 2)

    def test_allowed_types_and_validation(self):
        out = irun(fake_llm({"images": [img(source_type="ai_generated"), img()]}), constraints={"allowed_source_types": ["own"]})["output"]
        self.assertEqual([i["source_type"] for i in out["image_plan"]], ["own"])
        assert_error(self, irun(fake_llm({}), constraints={"max_images": 0}), "INVALID_INPUT")
        assert_error(self, irun(fake_llm({"images": []})), "INVALID_JSON")


FACT_ARTICLE = "# 제목\n\n## 방법\n\n월 10만원을 받습니다. 자세한 내용은 https://www.fss.or.kr/a 에서 확인하세요.\n\n> 본 글은 투자 권유가 아닙니다."


def adapted(**over):
    d = {"title": "새 제목", "body_markdown": "## 방법\n\n매달 10만원을 받게 됩니다. 더 알고 싶다면 https://www.fss.or.kr/a 를 보세요.\n\n> 본 글은 투자 권유가 아닙니다.\n\n{{image:img1}}",
         "meta_description": "메타", "summary": "말투 변경"}
    d.update(over)
    return d


def prun(llm, **over):
    inp = {"article_markdown": FACT_ARTICLE, "title": "제목", "platform": "naver", "content_type": "guide",
           "images": [{"image_id": "img1", "status": "RIGHTS_CONFIRMED", "url": "https://img.example.com/1.png", "alt_text": "설명"}]}
    inp.update(over)
    return pa.run(request("platform-adaptation", inp, content_id=CID), llm=llm)


class PlatformAdaptationTests(unittest.TestCase):
    def test_naver_and_blogspot_outputs(self):
        out = prun(fake_llm(adapted()))["output"]
        self.assertEqual(out["artifact"]["file_name"], f"{CID}_naver_v001.html")
        self.assertEqual(out["artifact"]["drive_path"], f"content/{CID}/publishing/naver")
        self.assertIn('<img src="https://img.example.com/1.png"', out["artifact"]["content"])
        self.assertNotIn("<h2>", out["artifact"]["content"])
        blog = prun(fake_llm(adapted()), platform="blogspot", output_version_no=2)["output"]
        self.assertEqual(blog["artifact"]["file_name"], f"{CID}_blogspot_v002.html")
        self.assertIn("<h2>방법</h2>", blog["artifact"]["content"])

    def test_unconfirmed_image_omitted(self):
        images = [{"image_id": "img1", "status": "PENDING_RIGHTS", "url": "https://img.example.com/1.png"}]
        out = prun(fake_llm(adapted()), images=images)["output"]
        self.assertNotIn("<img", out["artifact"]["content"])
        self.assertEqual(out["warnings"][0]["code"], "IMAGE_OMITTED")

    def test_fact_changes_rejected(self):
        for body in ("월 20만원을 받습니다. https://www.fss.or.kr/a 투자 권유가 아닙니다.",
                     "월 10만원을 받습니다. 투자 권유가 아닙니다.",
                     "월 10만원을 받습니다. https://www.fss.or.kr/a"):
            llm = fake_llm(adapted(body_markdown=body))
            assert_error(self, prun(llm), "QUALITY_BELOW_THRESHOLD")

    def test_duplicate_across_platforms_rejected(self):
        other = adapted()["body_markdown"]
        assert_error(self, prun(fake_llm(adapted()), other_platform_output=other), "QUALITY_BELOW_THRESHOLD")
        different = "## 방법\n\n한 달에 10만원이 입금되는 구조예요. 공식 안내는 https://www.fss.or.kr/a 에 있어요.\n\n> 본 글은 투자 권유가 아닙니다."
        self.assertIn("output", prun(fake_llm(adapted(body_markdown=different)), other_platform_output="전혀 다른 문장으로 쓰인 완전히 별개의 긴 글 " * 5))

    def test_invalid_platform(self):
        assert_error(self, prun(fake_llm(adapted()), platform="tistory"), "INVALID_INPUT")


def m(platform, name, value, at):
    return {"platform": platform, "metric_name": name, "metric_value": value, "measured_at": at}


def frun(inp, llm=None):
    return pf.run(request("performance-analysis", inp, content_id=CID), llm=llm)


class PerformanceAnalysisTests(unittest.TestCase):
    def test_aggregation_and_rules(self):
        rows = [m("naver", "views", 1000, "2026-11-01"), m("naver", "views", 500, "2026-11-08"), m("naver", "likes", 1, "2026-11-08"),
                m("naver", "bounce_rate", 0.8, "2026-11-08"), m("blogspot", "views", 100, "2026-11-08"), m("blogspot", "custom", 1, "2026-11-08")]
        out = frun({"metrics": rows})["output"]
        views = next(s for s in out["summary"] if s["platform"] == "naver" and s["metric_name"] == "views")
        self.assertEqual(views["latest"], 500)
        self.assertEqual(views["change_vs_previous"], -500)
        self.assertEqual(views["change_ratio"], -0.5)
        types = {s["type"] for s in out["suggestions"]}
        self.assertTrue({"engagement", "bounce", "decline"} <= types)
        self.assertEqual(out["warnings"][0]["code"], "UNKNOWN_METRICS")

    def test_ai_suggestions_added(self):
        llm = fake_llm({"suggestions": [{"platform": "naver", "basis": "조회수 500", "suggestion": "제목을 바꿔 볼 수 있습니다(가설)"}, {"suggestion": ""}]})
        out = frun({"metrics": [m("naver", "views", 500, "2026-11-08")]}, llm)["output"]
        # likes/comments were not collected, so no engagement rule fires (missing is not zero)
        self.assertEqual([s["type"] for s in out["suggestions"]], ["ai"])

    def test_validation(self):
        assert_error(self, frun({"metrics": []}), "INVALID_INPUT")
        assert_error(self, frun({"metrics": [m("tistory", "views", 1, "d")]}), "INVALID_INPUT")
        assert_error(self, frun({"metrics": [m("naver", "views", -1, "d")]}), "INVALID_INPUT")


class CliTests(unittest.TestCase):
    def test_run_skill_cli(self):
        import run_skill
        req = request("performance-analysis", {"metrics": [m("naver", "views", 10, "2026-11-01")]}, content_id=CID)
        stdin = io.TextIOWrapper(io.BytesIO(json.dumps(req).encode("utf-8")), encoding="utf-8")
        stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        with mock.patch("sys.stdin", stdin), mock.patch("sys.stdout", stdout):
            code = run_skill.main(["performance-analysis"])
            stdout.flush()
            stdout.buffer.seek(0)
            body = json.loads(stdout.buffer.read().decode("utf-8"))
        self.assertEqual(code, 0)
        self.assertIn("output", body)


if __name__ == "__main__":
    unittest.main()
