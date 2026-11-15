import unittest

import helpers
from helpers import CID, NOW, TID, assert_error, fake_llm, fake_search, request
from common.loader import load_skill

sr = load_skill("source-research")
cp = load_skill("content-planning")

RESULTS = [
    {"title": "금융감독원 안내", "url": "https://www.fss.or.kr/a", "publisher": "금융감독원", "snippet": "공식 안내", "published_at": "2026-01-02"},
    {"title": "블로그 글", "url": "https://blog.example.com/b", "publisher": "블로그", "snippet": "후기"},
    {"title": "뉴스 기사", "url": "https://news.example.com/c", "publisher": "뉴스", "snippet": "기사"},
]


def item(ref, stype="secondary", summary="요약입니다"):
    return {"source_ref": ref, "source_type": stype, "evidence_summary": summary, "answers_questions": ["Q1"]}


def sinp(ctype="guide", **over):
    base = {"topic": {"title": "아동수당 신청 방법", "content_type": ctype}, "research_questions": ["누가 받을 수 있나"]}
    base.update(over)
    return base


def srun(llm, inp, results=RESULTS):
    return sr.run(request("source-research", inp, content_id=CID, topic_id=TID), llm=llm, search=fake_search(results), now=NOW)


class SourceResearchTests(unittest.TestCase):
    def test_success_marks_official_by_domain_only(self):
        llm = fake_llm({"items": [item("S1", "secondary"), item("S2", "official"), item("S3")], "gaps": ["지급일 미확인"]})
        out = srun(llm, sinp())["output"]
        by_url = {s["source_url"]: s for s in out["sources"]}
        self.assertEqual(by_url["https://www.fss.or.kr/a"]["source_type"], "official")
        self.assertEqual(by_url["https://blog.example.com/b"]["source_type"], "secondary")  # model claim ignored
        self.assertEqual(out["sources"][0]["source_type"], "official")
        self.assertEqual(out["sources"][0]["verification_status"], "unverified")
        self.assertEqual(out["sources"][0]["published_at"], "2026-01-02")
        self.assertEqual(out["artifact"]["file_name"], f"{CID}_research_v001.md")
        self.assertIn("지급일 미확인", out["artifact"]["content"])

    def test_fabricated_ref_ignored_and_min_sources(self):
        llm = fake_llm({"items": [item("S1"), item("S9"), item("S2", summary="")]})
        assert_error(self, srun(llm, sinp()), "INSUFFICIENT_EVIDENCE")

    def test_finance_requires_official(self):
        llm = fake_llm({"items": [item("S2"), item("S3")]})
        assert_error(self, srun(llm, sinp("finance", source_criteria={"min_sources": 2})), "INSUFFICIENT_EVIDENCE")

    def test_validation_and_privacy(self):
        assert_error(self, srun(fake_llm({}), sinp(research_questions=[])), "INVALID_INPUT")
        assert_error(self, srun(fake_llm({}), sinp(research_questions=["연락처 010-1111-2222"])), "INVALID_INPUT")
        assert_error(self, srun(fake_llm({}), sinp(), results=[]), "INSUFFICIENT_EVIDENCE")


RESEARCH = [{"research_id": "r1", "source_title": "공식", "evidence_summary": "월 10만원 지급"},
            {"research_id": "r2", "source_title": "기사", "evidence_summary": "신청은 온라인 가능"}]


def plan(**over):
    p = {"working_title": "아동수당 신청 방법", "direction": "처음 신청하는 부모용", "key_message": "온라인으로 쉽게 신청",
         "target_reader": "신생아 부모",
         "outline": [{"heading": "대상", "points": ["대상 확인"], "research_ids": ["r1"]},
                     {"heading": "절차", "points": ["온라인 신청"], "research_ids": ["r2"]},
                     {"heading": "주의", "points": ["기한"], "research_ids": []}],
         "interview_focus": ["신청 과정에서 막혔던 점", "걸린 시간"], "comparison_criteria": ["가격", "기능", "크기"]}
    p.update(over)
    return p


def cinp(ctype="guide", **over):
    base = {"topic": {"title": "아동수당 신청 방법", "content_type": ctype}, "research_sources": RESEARCH}
    base.update(over)
    return base


def crun(llm, inp):
    return cp.run(request("content-planning", inp, content_id=CID, topic_id=TID), llm=llm, now=NOW)


class ContentPlanningTests(unittest.TestCase):
    def test_success_and_artifact(self):
        out = crun(fake_llm(plan()), cinp())["output"]
        self.assertEqual(len(out["plan"]["outline"]), 3)
        self.assertEqual(out["artifact"]["file_name"], f"{CID}_plan_v001.md")
        self.assertIn("## 목차", out["artifact"]["content"])

    def test_finance_gets_notice_section(self):
        out = crun(fake_llm(plan()), cinp("finance"))["output"]
        self.assertIn("유의사항", out["plan"]["outline"][-1]["heading"])
        self.assertTrue(out["plan"]["requires_finance_notice"])

    def test_unknown_research_id_is_repaired_then_fails(self):
        bad = plan(outline=[{"heading": "a", "points": ["x"], "research_ids": ["zzz"]}] * 3)
        assert_error(self, crun(fake_llm(bad), cinp()), "INVALID_JSON")

    def test_type_specific_requirements(self):
        assert_error(self, crun(fake_llm(plan(interview_focus=["하나"])), cinp("experience")), "INVALID_JSON")
        assert_error(self, crun(fake_llm(plan(comparison_criteria=["하나"])), cinp("compare")), "INVALID_JSON")
        ok = crun(fake_llm(plan()), cinp("compare"))["output"]["plan"]
        self.assertEqual(len(ok["comparison_criteria"]), 3)

    def test_input_validation(self):
        assert_error(self, crun(fake_llm(plan()), cinp(research_sources=[])), "INVALID_INPUT")
        assert_error(self, crun(fake_llm(plan()), cinp("travel")), "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
