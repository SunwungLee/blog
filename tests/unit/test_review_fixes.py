"""Regression tests for issues found in the code review and design audit."""

import io
import json
import unittest
from unittest import mock

import helpers
from helpers import CID, NOW, TID, TODAY, assert_error, fake_llm, fake_search, request
from common import ids, privacy
from common.config import role_for
from common.errors import SkillError
from common.facts import facts_changed
from common.llm import call_json
from common.loader import load_module, load_script, load_skill
from common.sources import run_search
from common.util import FIRST_PERSON

ma = load_skill("master-article")
iq = load_skill("interview-questioning")
sr = load_skill("source-research")
fc = load_skill("fact-checking")
seo = load_skill("seo-optimization")
pa = load_skill("platform-adaptation")
ip = load_skill("image-preparation")
pf = load_skill("performance-analysis")
td = load_skill("topic-discovery")
dv = load_script("data-validator")
hc = load_script("html-converter")

FILLER = "내용을 차근차근 자세히 설명해 드립니다. " * 50
PLAN = {"direction": "d", "key_message": "k", "outline": [{"heading": "대상", "points": ["a"]}, {"heading": "절차", "points": ["b"]}]}
RESEARCH = [{"research_id": "r1", "source_title": "공식", "source_url": "https://www.fss.or.kr/a", "evidence_summary": "월 10만원 지급",
             "source_type": "official", "accessed_at": "2026-11-01T09:00:00+09:00"},
            {"research_id": "r2", "source_title": "기사", "source_url": "https://news.example.com/c", "evidence_summary": "온라인 신청 가능"}]


def article(extra=""):
    return {"title": "아동수당 신청 방법", "body_markdown": f"## 대상\n\n{FILLER}\n\n## 절차\n\n{FILLER}\n{extra}", "used_research_ids": ["r1"], "warnings": []}


def mrun(llm, ctype="guide", **over):
    inp = {"content_type": ctype, "plan": PLAN, "research_sources": RESEARCH,
           "answers": [{"question_id": "q1", "question_text": "계기는?", "answer_text": "친구 추천"}]}
    inp.update(over)
    return ma.run(request("master-article", inp, content_id=CID), llm=llm, now=NOW)


class PrivacyAndTextRules(unittest.TestCase):
    def test_numbers_followed_by_korean_are_detected(self):
        self.assertIn("phone", privacy.find_pii("연락처는 010-1234-5678입니다"))
        self.assertIn("resident_number", privacy.find_pii("900101-1234567이고"))
        self.assertIn("address", privacy.find_pii("101동 1203호에 살아요"))
        self.assertIn("address", privacy.find_pii("경기도 성남시 분당구"))

    def test_ordinary_sentences_are_not_addresses(self):
        for text in ("하루 기준으로 3번", "만원으로 2배", "이 정도 활용하시면", "적정 온도 연구", "2026년 상반기"):
            self.assertEqual(privacy.find_pii(text), [], text)

    def test_redact_masks_terms_and_patterns(self):
        text, kinds = privacy.redact("김철수 010-1234-5678입니다", ["김철수"])
        self.assertNotIn("김철수", text)
        self.assertNotIn("5678", text)
        self.assertEqual(set(kinds), {"phone", "blocked_term"})

    def test_first_person_needs_word_start(self):
        for word in ("문제가", "경제가", "소득공제가", "최저는"):
            self.assertIsNone(FIRST_PERSON.search(word), word)
        self.assertIsNotNone(FIRST_PERSON.search("제가 직접 써 봤습니다"))

    def test_ids_reject_trailing_newline(self):
        self.assertFalse(ids.is_content_id(CID + "\n"))
        self.assertTrue(dv.validate_envelope(request("m", {}, content_id=CID + "\n")))

    def test_facts_changed_edge_cases(self):
        self.assertTrue(facts_changed("본문", "본문 https://evil.example.com"))
        self.assertEqual(facts_changed("- 하나\n- 둘", "1. 하나\n2. 둘"), [])
        self.assertEqual(facts_changed("출처 https://a.com/x.", "출처: https://a.com/x"), [])
        self.assertTrue(facts_changed("본문", "본문 ![x](https://img.example.com/a.png)"))


class EnvelopeProvidersLoader(unittest.TestCase):
    def test_bad_content_id_rejected_before_model_call(self):
        llm = fake_llm(article())
        resp = ma.run(request("master-article", {}, content_id="bad"), llm=llm, now=NOW)
        assert_error(self, resp, "INVALID_INPUT")
        self.assertEqual(llm.calls, [])

    def test_provider_errors_map_to_retryable_codes(self):
        def timeout(*a):
            raise TimeoutError("secret-token")

        class Http(Exception):
            code = 429

        def limited(*a):
            raise Http()

        with self.assertRaises(SkillError) as ctx:
            call_json(timeout, "lightweight", "s", "p")
        self.assertEqual((ctx.exception.code, ctx.exception.retryable), ("API_TRANSIENT", True))
        self.assertNotIn("secret", ctx.exception.message)
        with self.assertRaises(SkillError) as ctx:
            run_search(limited, "q")
        self.assertEqual(ctx.exception.code, "API_RATE_LIMITED")

    def test_wrong_types_in_validator_trigger_repair(self):
        replies = iter(['{"a": null}', '{"a": [1]}'])
        data = call_json(lambda *a: next(replies), "lightweight", "s", "p", lambda d: d if len(d["a"]) else None)
        self.assertEqual(data, {"a": [1]})

    def test_search_results_are_capped(self):
        many = [{"title": f"t{i}", "url": f"https://x{i}.com"} for i in range(20)]
        self.assertEqual(len(run_search(lambda q, n: many, "q", 3)), 3)

    def test_loader_rejects_traversal(self):
        for name in ("../../evil", "..", "a/b", "Topic"):
            with self.assertRaises(ModuleNotFoundError):
                load_module("skills", name)

    def test_role_comes_from_config(self):
        self.assertEqual(role_for("fact_checking", "x"), "high_quality")
        self.assertEqual(role_for("unknown_task", "lightweight"), "lightweight")

    def test_artifact_has_checksum_and_response_is_valid_envelope(self):
        resp = mrun(fake_llm(article()))
        self.assertEqual(dv.validate_envelope(resp), [])
        art = resp["output"]["artifact"]
        self.assertEqual(art["checksum"], ids.checksum(art["content"]))


class MasterArticleFixes(unittest.TestCase):
    def test_notices_added_even_if_keywords_appear(self):
        body = "광고 문구와 불법 투자 권유 전화에 주의하세요."
        content = mrun(fake_llm(article(body)), "finance", sponsored=True)["output"]["artifact"]["content"]
        self.assertIn(ma.FINANCE_NOTICE, content)
        self.assertIn(ma.SPONSOR_NOTICE, content)
        self.assertIn("정보 기준일: 2026-11-01", content)  # newest access date of cited sources

    def test_answers_are_redacted_before_prompt(self):
        llm = fake_llm(article())
        answers = [{"question_id": "q1", "question_text": "계기는?", "answer_text": "김민준이 010-1234-5678로 알려줬어요"}]
        out = mrun(llm, answers=answers, blocked_terms=["김민준"])["output"]
        prompt = llm.calls[0][1]
        self.assertNotIn("김민준", prompt)
        self.assertNotIn("5678", prompt)
        self.assertIn("PII_REDACTED", [w["code"] for w in out["warnings"]])

    def test_common_words_do_not_count_as_fake_experience(self):
        llm = fake_llm(article("이 제도의 문제가 무엇인지 경제가 어떤지 살펴봅니다."))
        self.assertIn("output", mrun(llm, answers=[]))


class InterviewFixes(unittest.TestCase):
    TEMPLATES = [{"question_id": "c1", "question": "계기는?", "required": True}]

    def test_blocked_terms_hide_answer(self):
        llm = fake_llm({"conflicts": [], "followups": []})
        answers = [{"question_id": "c1", "question_text": "계기는?", "answer_text": "지우가 좋아해서"}]
        out = iq.run(request("interview-questioning", {"content_type": "guide", "templates": self.TEMPLATES, "answers": answers,
                                                       "blocked_terms": ["지우"]}, content_id=CID), llm=llm)["output"]
        self.assertNotIn("지우", llm.calls[0][1])
        self.assertIn("PII_IN_ANSWER", [w["code"] for w in out["warnings"]])

    def test_no_provider_warns(self):
        answers = [{"question_id": "c1", "question_text": "계기는?", "answer_text": "추천"}]
        out = iq.run(request("interview-questioning", {"content_type": "guide", "templates": self.TEMPLATES, "answers": answers},
                             content_id=CID))["output"]
        self.assertIn("GAP_ANALYSIS_SKIPPED", [w["code"] for w in out["warnings"]])


class ResearchAndFactFixes(unittest.TestCase):
    RESULTS = [{"title": "금융감독원 안내", "url": "https://www.fss.or.kr/a", "snippet": "월 10만원 지급"},
               {"title": "블로그", "url": "https://blog.example.com/b", "snippet": "후기"}]

    def test_summary_with_invented_number_is_dropped(self):
        items = [{"source_ref": "S1", "evidence_summary": "월 10만원 지급"}, {"source_ref": "S2", "evidence_summary": "수익률 30% 보장"}]
        resp = sr.run(request("source-research", {"topic": {"title": "아동수당", "content_type": "guide"}, "research_questions": ["금액"],
                                                  "source_criteria": {"min_sources": 1}}, content_id=CID, topic_id=TID),
                      llm=fake_llm({"items": items}), search=fake_search(self.RESULTS), now=NOW)["output"]
        self.assertEqual([s["source_url"] for s in resp["sources"]], ["https://www.fss.or.kr/a"])
        self.assertIn("SUMMARY_NUMBER_NOT_IN_SOURCE", [w["code"] for w in resp["warnings"]])

    def _fc(self, claims, **over):
        inp = {"article_markdown": "# t\n\n신청은 온라인으로 할 수 있습니다.\n", "content_type": "finance",
               "research_sources": [{"research_id": "r2", "evidence_summary": "온라인 신청 가능"}], "article_version_id": "av-1"}
        inp.update(over)
        return fc.run(request("fact-checking", inp, content_id=CID), llm=fake_llm({"claims": claims}), now=NOW)

    def test_finance_without_source_type_is_not_official(self):
        out = self._fc([{"claim_text": "신청은 온라인으로 할 수 있습니다.", "result": "supported", "research_id": "r2"}])["output"]
        self.assertEqual(out["claims"][0]["result"], "unverifiable")
        self.assertEqual(out["claims"][0]["created_by_run_id"], "run-1")

    def test_unhashable_research_id_and_missing_version(self):
        out = self._fc([{"claim_text": "신청은 온라인으로 할 수 있습니다.", "result": "supported", "research_id": ["r2"]}])
        self.assertEqual(out["output"]["claims"][0]["result"], "unverifiable")
        assert_error(self, self._fc([], article_version_id=None), "INVALID_INPUT")


def seo_body(kw="이유식 시작 시기"):
    return (f"# 제목\n\n{kw}를 알아봅니다. 월 10만원 기준입니다.\n\n## {kw} 준비물\n\n" + "내용을 설명합니다. " * 120 +
            "\n\n## 마무리\n\n" + "정리합니다. " * 30)


META = "이유식을 언제 어떻게 시작하는지, 준비물과 진행 순서를 한 번에 정리했습니다. 처음 이유식을 시작하는 부모님을 위한 단계별 안내입니다."


def srun(llm, **over):
    inp = {"article_markdown": seo_body(), "title": "이유식 시작 시기와 준비물 완벽 정리 가이드", "primary_keyword": "이유식 시작 시기",
           "related_keywords": ["준비물"], "meta_description": META, "seo_config": {"min_chars": 500}}
    inp.update(over)
    return seo.run(request("seo-optimization", inp, content_id=CID), llm=llm)


class SeoFixes(unittest.TestCase):
    def test_title_only_failure_does_not_send_or_change_body(self):
        llm = fake_llm({"title": "이유식 시작 시기와 준비물 완벽 정리 가이드", "meta_description": META, "changes": ["제목"]})
        out = srun(llm, title="짧은 제목")["output"]
        self.assertFalse(out["requires_refactcheck"])
        self.assertEqual(out["artifact"]["content"].strip(), seo_body().strip())
        self.assertLess(len(llm.calls[0][1]), len(seo_body()))

    def test_added_sentences_and_title_numbers_rejected(self):
        grown = {"title": "t", "meta_description": "m", "body_markdown": seo_body() + "\n\n" + "새로운 사실을 덧붙입니다. " * 80}
        assert_error(self, srun(fake_llm(grown), article_markdown=seo_body("다른 말")), "QUALITY_BELOW_THRESHOLD")
        numbered = {"title": "이유식 시작 시기 99가지", "meta_description": META, "body_markdown": seo_body()}
        assert_error(self, srun(fake_llm(numbered), article_markdown=seo_body("다른 말")), "QUALITY_BELOW_THRESHOLD")

    def test_body_rewrite_requires_refactcheck(self):
        good = {"title": "이유식 시작 시기와 준비물 완벽 정리 가이드", "meta_description": META, "body_markdown": seo_body(), "changes": None}
        out = srun(fake_llm(good), article_markdown=seo_body("다른 말"))["output"]
        self.assertTrue(out["requires_refactcheck"])
        self.assertEqual(out["changes"], [])


ART = "# 제목\n\n## 방법\n\n월 10만원을 받습니다. 자세한 내용은 https://www.fss.or.kr/a 에서 확인하세요."


def prun(body, **over):
    inp = {"article_markdown": ART, "title": "제목", "platform": "naver", "content_type": "guide"}
    inp.update(over)
    return pa.run(request("platform-adaptation", inp, content_id=CID), llm=fake_llm({"title": "t", "body_markdown": body}))


class PlatformFixes(unittest.TestCase):
    def test_both_platforms_without_other_checks_master_overlap(self):
        assert_error(self, prun(ART, target_platforms=["naver", "blogspot"]), "QUALITY_BELOW_THRESHOLD")
        different = "## 방법\n\n한 달에 10만원이 들어오는 구조예요. 공식 안내는 https://www.fss.or.kr/a 에 있어요."
        out = prun(different, target_platforms=["naver", "blogspot"])["output"]
        self.assertIn("DUPLICATE_CHECK_PENDING", [w["code"] for w in out["warnings"]])

    def test_stock_phrases_rejected(self):
        assert_error(self, prun(ART.replace("자세한", "결론적으로 자세한")), "QUALITY_BELOW_THRESHOLD")


class HtmlConverterFixes(unittest.TestCase):
    def test_links_with_ampersand_and_emphasis_markers(self):
        out = hc.markdown_to_html("[출처](https://a.com/?a=1&b=2) [x](https://a.com/*a*/b)")
        self.assertIn('href="https://a.com/?a=1&amp;b=2"', out)
        self.assertNotIn("&amp;amp;", out)
        self.assertIn('href="https://a.com/*a*/b"', out)

    def test_protocol_relative_and_backslash_urls_blocked(self):
        out = hc.markdown_to_html("[a](//evil.com) [b](/\\evil.com) [c](&#106;avascript:alert(1))")
        self.assertNotIn("evil.com", out)
        self.assertNotIn("javascript", out)

    def test_nul_input_and_blocks_after_paragraph(self):
        self.assertIn("<p>", hc.markdown_to_html("a\x000\x00b"))
        out = hc.markdown_to_html("문단\n| a | b |\n|---|---|\n| 1 | 2 |\n문단2\n---")
        self.assertIn("<table>", out)
        self.assertIn("<hr>", out)


class OtherSkillFixes(unittest.TestCase):
    def test_image_preparation_validation_and_missing_id(self):
        run = lambda **inp: ip.run(request("image-preparation", {"article_markdown": "## a\n\n본문", **inp}, content_id=CID),
                                   llm=fake_llm({"images": [{"alt_text": "식탁", "purpose": "p", "source_type": "own"}]}), now=NOW)
        for bad in ({"constraints": {"max_width": 0}}, {"constraints": {"max_width": "abc"}}, {"constraints": "x"}):
            assert_error(self, run(**bad), "INVALID_INPUT")
        asset = {"source_type": "own", "drive_file_id": "f1", "rights_note": "직접 촬영", "rights_checked_at": "2026-11-12"}
        out = run(assets=[asset])["output"]
        self.assertEqual(out["usable_image_ids"], [])
        self.assertIn("image_id 없음", out["assets"][0]["problems"][0])

    def test_performance_time_order_and_validation(self):
        rows = [{"platform": "naver", "metric_name": "views", "metric_value": 10, "measured_at": "2026-11-02T00:00:00+09:00"},
                {"platform": "naver", "metric_name": "views", "metric_value": 20, "measured_at": "2026-11-01T20:00:00Z"}]
        out = pf.run(request("performance-analysis", {"metrics": rows}, content_id=CID))["output"]
        self.assertEqual(out["summary"][0]["latest"], 20)  # 20:00Z is later than 00:00+09:00
        rows[0]["measured_at"] = "어제"
        assert_error(self, pf.run(request("performance-analysis", {"metrics": rows}, content_id=CID)), "INVALID_INPUT")

    def test_review_topics_need_firsthand_experience(self):
        results = [{"title": f"자료 {i}", "url": f"https://site{i}.example.com/a", "snippet": "내용"} for i in range(1, 8)]
        words = ["유모차", "카시트", "젖병", "아기띠", "기저귀"]
        cands = [{"content_type": "review", "candidate_title": f"{w} 사용 후기", "primary_keyword": w, "related_keywords": ["a", "b", "c"],
                  "search_intent": "i", "rationale": "r", "freshness": "evergreen", "source_refs": ["S1"]} for w in words]
        out = td.run(request("topic-discovery", {"editorial_context": "육아", "active_content_types": ["review"]}, discovery_run_id="d1"),
                     llm=fake_llm({"candidates": cands}), search=fake_search(results), now=NOW, today=TODAY)["output"]
        self.assertTrue(all(c["requires_firsthand_experience"] for c in out["candidates"]))


def _cli(main, argv, raw_bytes):
    stdin = io.TextIOWrapper(io.BytesIO(raw_bytes), encoding="utf-8")
    stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    with mock.patch("sys.stdin", stdin), mock.patch("sys.stdout", stdout):
        code = main(argv)
        stdout.flush()
        stdout.buffer.seek(0)
        return code, json.loads(stdout.buffer.read().decode("utf-8"))


class CliFixes(unittest.TestCase):
    REQ = request("performance-analysis", {"metrics": [{"platform": "naver", "metric_name": "views", "metric_value": 1, "measured_at": "2026-11-01"}]},
                  content_id=CID)

    def test_bom_is_accepted(self):
        import run_skill
        code, body = _cli(run_skill.main, ["performance-analysis"], b"\xef\xbb\xbf" + json.dumps(self.REQ).encode("utf-8"))
        self.assertEqual(code, 0, body)

    def test_missing_providers_module_returns_envelope(self):
        import run_skill
        code, body = _cli(run_skill.main, ["performance-analysis", "--providers", "no_such_providers_mod"], json.dumps(self.REQ).encode("utf-8"))
        self.assertEqual(code, 1)
        self.assertEqual(body["error"]["code"], "AUTH_OR_PERMISSION")

    def test_run_script(self):
        import run_script
        req = request("html-converter", {"markdown": "## 제목", "target": "naver"})
        code, body = _cli(run_script.main, ["html-converter"], json.dumps(req).encode("utf-8"))
        self.assertEqual(code, 0, body)
        self.assertIn("■ 제목", body["output"]["html"])
        code, body = _cli(run_script.main, ["image-processor"], json.dumps(request("image-processor", {"width": 2400, "height": 1200})).encode("utf-8"))
        self.assertEqual(body["output"], {"width": 1200, "height": 600})


if __name__ == "__main__":
    unittest.main()
