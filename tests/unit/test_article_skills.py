import unittest

import helpers
from helpers import CID, NOW, assert_error, fake_llm, request
from common.loader import load_skill

ma = load_skill("master-article")
fc = load_skill("fact-checking")
seo = load_skill("seo-optimization")

PLAN = {"direction": "d", "key_message": "k", "outline": [{"heading": "대상", "points": ["a"]}, {"heading": "절차", "points": ["b"]}]}
RESEARCH = [{"research_id": "r1", "source_title": "공식", "source_url": "https://www.fss.or.kr/a", "evidence_summary": "월 10만원 지급", "source_type": "official"},
            {"research_id": "r2", "source_title": "기사", "source_url": "https://news.example.com/c", "evidence_summary": "온라인 신청 가능", "source_type": "secondary"}]
FILLER = "내용을 차근차근 자세히 설명해 드립니다. " * 50


def body(extra=""):
    return f"## 대상\n\n{FILLER}\n\n## 절차\n\n{FILLER}\n{extra}"


def article(**over):
    d = {"title": "아동수당 신청 방법", "body_markdown": body(), "used_research_ids": ["r1"], "warnings": []}
    d.update(over)
    return d


def minp(ctype="guide", **over):
    base = {"content_type": ctype, "plan": PLAN, "research_sources": RESEARCH,
            "answers": [{"question_id": "q1", "question_text": "계기는?", "answer_text": "친구 추천"}]}
    base.update(over)
    return base


def mrun(llm, inp):
    return ma.run(request("master-article", inp, content_id=CID), llm=llm, now=NOW)


class MasterArticleTests(unittest.TestCase):
    def test_success_with_references_and_file_name(self):
        out = mrun(fake_llm(article()), minp())["output"]
        content = out["artifact"]["content"]
        self.assertEqual(out["artifact"]["file_name"], f"{CID}_master_v001.md")
        self.assertIn("## 참고 자료", content)
        self.assertIn("https://www.fss.or.kr/a", content)

    def test_finance_adds_notice_and_reference_date(self):
        content = mrun(fake_llm(article()), minp("finance"))["output"]["artifact"]["content"]
        self.assertIn("투자 권유", content)
        self.assertIn("정보 기준일: 2026-11-12", content)

    def test_banned_finance_language_triggers_rerun_then_ok(self):
        llm = fake_llm(article(body_markdown=body("이 상품은 수익 보장입니다.")), article())
        out = mrun(llm, minp("finance"))
        self.assertIn("output", out)
        self.assertEqual(len(llm.calls), 2)
        self.assertIn("이전 결과의 문제", llm.calls[1][1])

    def test_quality_exhaustion(self):
        llm = fake_llm(article(body_markdown="너무 짧음"))
        assert_error(self, mrun(llm, minp()), "QUALITY_BELOW_THRESHOLD")
        self.assertEqual(len(llm.calls), 3)  # initial + 2 reruns

    def test_unprovided_experience_and_fake_citation_rejected(self):
        assert_error(self, mrun(fake_llm(article(body_markdown=body("제가 직접 겪어보니 좋았습니다."))), minp(answers=[])), "QUALITY_BELOW_THRESHOLD")
        assert_error(self, mrun(fake_llm(article(used_research_ids=["zzz"])), minp()), "QUALITY_BELOW_THRESHOLD")

    def test_experience_needs_real_answers(self):
        assert_error(self, mrun(fake_llm(article()), minp("experience", answers=[])), "INSUFFICIENT_EVIDENCE")
        only_unknown = [{"question_id": "q", "question_text": "?", "answer_text": "모름"}]
        assert_error(self, mrun(fake_llm(article()), minp("review", answers=only_unknown)), "INSUFFICIENT_EVIDENCE")

    def test_dont_know_warning_and_sponsor_notice(self):
        answers = [{"question_id": "q1", "question_text": "계기는?", "answer_text": "추천"},
                   {"question_id": "q2", "question_text": "가격은?", "answer_text": "모름"}]
        out = mrun(fake_llm(article()), minp("review", answers=answers, sponsored=True))["output"]
        self.assertIn("DONT_KNOW_OMITTED", [w["code"] for w in out["warnings"]])
        self.assertTrue(out["artifact"]["content"].startswith("> 본 글에는 광고"))

    def test_stock_ai_phrases_rejected(self):
        llm = fake_llm(article(body_markdown=body("결론적으로 좋습니다.")), article())
        out = mrun(llm, minp())
        self.assertIn("output", out)
        self.assertIn("상투 표현", llm.calls[1][1])
        self.assertIn("사람이 직접 쓴 것처럼", llm.calls[0][1])

    def test_pii_in_article_rejected(self):
        assert_error(self, mrun(fake_llm(article(body_markdown=body("문의 a@b.com"))), minp()), "QUALITY_BELOW_THRESHOLD")


ART = "# 제목\n\n월 10만원이 지급됩니다. 신청은 온라인으로 할 수 있습니다. 많은 부모가 만족합니다.\n\n## 참고 자료\n- x"


def claim(text, result="supported", rid="r1", note=""):
    return {"claim_text": text, "result": result, "research_id": rid, "note": note}


def frun(llm, inp=None, **over):
    base = {"article_markdown": ART, "content_type": "guide", "research_sources": RESEARCH, "article_version_id": "av-1"}
    base.update(inp or {})
    base.update(over)
    return fc.run(request("fact-checking", base, content_id=CID), llm=llm, now=NOW)


class FactCheckingTests(unittest.TestCase):
    def test_pass(self):
        llm = fake_llm({"claims": [claim("월 10만원이 지급됩니다."), claim("신청은 온라인으로 할 수 있습니다.", rid="r2")]})
        out = frun(llm)["output"]
        self.assertTrue(out["passed"], out)
        self.assertEqual(out["counts"]["supported"], 2)
        self.assertTrue(all(len(c["fact_check_id"]) == 36 and c["content_id"] == CID for c in out["claims"]))

    def test_contradicted_fails(self):
        out = frun(fake_llm({"claims": [claim("월 10만원이 지급됩니다.", "contradicted")]}))["output"]
        self.assertFalse(out["passed"])
        self.assertEqual(len(out["unresolved_claims"]), 1)

    def test_invented_claim_ignored_and_bad_research_id_downgraded(self):
        llm = fake_llm({"claims": [claim("원고에 없는 문장입니다."), claim("월 10만원이 지급됩니다.", rid="zzz")]})
        out = frun(llm)["output"]
        self.assertEqual([c["claim_text"] for c in out["claims"]], ["월 10만원이 지급됩니다."])
        self.assertEqual(out["claims"][0]["result"], "unverifiable")

    def test_number_not_in_evidence_is_downgraded(self):
        art = "# t\n\n월 20만원이 지급됩니다.\n"
        out = frun(fake_llm({"claims": [claim("월 20만원이 지급됩니다.")]}), article_markdown=art)["output"]
        self.assertEqual(out["claims"][0]["result"], "unverifiable")
        self.assertFalse(out["passed"])

    def test_unlisted_numeric_sentence_is_added(self):
        out = frun(fake_llm({"claims": [claim("신청은 온라인으로 할 수 있습니다.", rid="r2")]}))["output"]
        added = [c for c in out["claims"] if "10만원" in c["claim_text"]]
        self.assertEqual(added[0]["result"], "unverifiable")

    def test_finance_needs_official_source(self):
        art = "# t\n\n신청은 온라인으로 할 수 있습니다.\n"
        llm = fake_llm({"claims": [claim("신청은 온라인으로 할 수 있습니다.", rid="r2")]})
        out = frun(llm, article_markdown=art, content_type="finance")["output"]
        self.assertEqual(out["claims"][0]["result"], "unverifiable")

    def test_errors(self):
        assert_error(self, frun(fake_llm({"claims": []}), article_markdown="# t\n\n좋은 글입니다.\n"), "INSUFFICIENT_EVIDENCE")
        assert_error(self, frun(fake_llm({}), research_sources=[]), "INSUFFICIENT_EVIDENCE")
        assert_error(self, frun(fake_llm({}), content_type="x"), "INVALID_INPUT")


def seo_body(kw="이유식 시작 시기", extra=""):
    return (f"# 제목\n\n{kw}를 알아봅니다. 월 10만원 기준입니다.\n\n## {kw} 준비물\n\n" + "내용을 설명합니다. " * 120 +
            f"\n\n## 마무리\n\n" + "정리합니다. " * 30 + extra)


def sinp(**over):
    base = {"article_markdown": seo_body(), "title": "이유식 시작 시기와 준비물 완벽 정리 가이드", "primary_keyword": "이유식 시작 시기",
            "related_keywords": ["준비물", "마무리"], "meta_description": "이유식을 언제 어떻게 시작하는지, 준비물과 진행 순서를 한 번에 정리했습니다. 처음 이유식을 시작하는 부모님을 위한 단계별 안내입니다.",
            "seo_config": {"min_chars": 500}}
    base.update(over)
    return base


def srun(llm, **over):
    return seo.run(request("seo-optimization", sinp(**over), content_id=CID), llm=llm)


class SeoOptimizationTests(unittest.TestCase):
    def test_passing_article_skips_ai(self):
        llm = fake_llm({})
        out = srun(llm)["output"]
        self.assertFalse(out["optimized"])
        self.assertEqual(llm.calls, [])
        self.assertEqual(out["artifact"]["file_name"], f"{CID}_final_v001.md")

    def test_rewrite_keeps_facts(self):
        weak = seo_body(kw="다른 말")
        good = {"title": "이유식 시작 시기와 준비물 완벽 정리 가이드", "meta_description": "이유식을 언제 어떻게 시작하는지, 준비물과 진행 순서를 한 번에 정리했습니다. 처음 이유식을 시작하는 부모님을 위한 단계별 안내입니다.",
                "body_markdown": seo_body(), "changes": ["소제목 수정"]}
        out = srun(fake_llm(good), article_markdown=weak, meta_description="")["output"]
        self.assertTrue(out["optimized"])
        self.assertFalse(out["before"]["passed"])
        self.assertTrue(out["after"]["passed"])

    def test_added_numbers_or_lost_links_rejected(self):
        weak = seo_body(kw="다른 말", extra="\n\n[출처](https://www.fss.or.kr/a)")
        bad = {"title": "t", "meta_description": "m", "body_markdown": seo_body() + " 수익률 99%"}
        llm = fake_llm(bad)
        assert_error(self, srun(llm, article_markdown=weak, meta_description=""), "QUALITY_BELOW_THRESHOLD")
        self.assertEqual(len(llm.calls), 3)


if __name__ == "__main__":
    unittest.main()
