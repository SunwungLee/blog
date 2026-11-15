import unittest

import helpers
from helpers import TODAY, NOW, assert_error, fake_llm, fake_search, request
from common.loader import load_skill

td = load_skill("topic-discovery")

RESULTS = [{"title": f"자료 {i}", "url": f"https://site{i}.example.com/a", "publisher": f"P{i}", "snippet": "내용"} for i in range(1, 8)]
RESULTS[1]["url"] = "https://www.fss.or.kr/guide"


WORDS = ["이유식 시작 시기", "자녀 증여 세금", "유모차 비교 분석", "어린이집 신청 방법", "카시트 사용 후기",
         "아동수당 지급일", "기저귀 가격 정리", "예방접종 일정표", "학자금 대출 안내", "돌잔치 준비 목록"]


def cand(i, ctype="guide", **over):
    c = {"content_type": ctype, "candidate_title": f"{WORDS[i % 10]} 총정리 {ctype}", "primary_keyword": f"키워드{i}",
         "related_keywords": ["a1", "a2", "a3"], "search_intent": "알고 싶다", "rationale": "근거가 있다",
         "freshness": "evergreen", "source_refs": ["S1"]}
    c.update(over)
    return c


def inp(**over):
    base = {"editorial_context": "육아 정보 블로그", "active_content_types": ["experience", "finance", "review", "guide", "compare"]}
    base.update(over)
    return base


def run(llm, i=None, search=None):
    return td.run(request("topic-discovery", i or inp(), discovery_run_id="d1"), llm=llm,
                  search=search or fake_search(RESULTS), now=NOW, today=TODAY)


class TopicDiscoveryTests(unittest.TestCase):
    def test_success_default_five_with_sources_and_no_ids(self):
        types = ["experience", "finance", "review", "guide", "compare", "guide"]
        out = run(fake_llm({"candidates": [cand(i, t) for i, t in enumerate(types)]}))["output"]
        self.assertEqual(len(out["candidates"]), 5)
        c = out["candidates"][0]
        self.assertNotIn("topic_id", c)
        self.assertEqual(c["sources"][0]["url"], RESULTS[0]["url"])
        self.assertEqual(c["sources"][0]["accessed_at"], "2026-11-12T15:00:00+09:00")
        self.assertTrue(c["requires_firsthand_experience"])

    def test_invalid_count_and_types(self):
        for bad in ({"candidate_count": 4}, {"candidate_count": 11}, {"requested_content_types": ["travel"]},
                    {"editorial_context": " "}):
            assert_error(self, run(fake_llm({}), inp(**bad)), "INVALID_INPUT")

    def test_privacy_blocks_before_search(self):
        s = fake_search(RESULTS)
        resp = run(fake_llm({}), inp(editorial_context="연락처 010-1234-5678 가족", ), s)
        assert_error(self, resp, "INVALID_INPUT")
        self.assertEqual(s.calls, [])
        resp = run(fake_llm({}), inp(blocked_terms=["수원"], discovery_criteria="수원 맛집"), s)
        assert_error(self, resp, "INVALID_INPUT")

    def test_search_budget_and_requires_discovery_run_id(self):
        s = fake_search(RESULTS)
        run(fake_llm({"candidates": [cand(i) for i in range(5)]}), search=s)
        self.assertLessEqual(len(s.calls), 2)
        resp = td.run(request("topic-discovery", inp()), llm=fake_llm({}), search=s)
        assert_error(self, resp, "INVALID_INPUT")

    def test_fabricated_sources_dropped_then_insufficient(self):
        cands = [cand(i, source_refs=["S99"]) for i in range(5)] + [cand(9)]
        assert_error(self, run(fake_llm({"candidates": cands})), "INSUFFICIENT_EVIDENCE")

    def test_partial_list_warns(self):
        resp = run(fake_llm({"candidates": [cand(i) for i in range(6)]}), inp(candidate_count=8))
        self.assertEqual(len(resp["output"]["candidates"]), 6)
        self.assertEqual(resp["output"]["warnings"][0]["code"], "REQUESTED_COUNT_NOT_MET")

    def test_rejects_measured_claims_and_first_person_titles(self):
        cands = [cand(0, rationale="검색량 5000 이상"), cand(1, candidate_title="제가 직접 겪은 이유식 후기 정리"),
                 *[cand(i) for i in range(2, 8)]]
        out = run(fake_llm({"candidates": cands}))["output"]
        titles = [c["candidate_title"] for c in out["candidates"]]
        self.assertNotIn("제가 직접 겪은 이유식 후기 정리", titles)
        self.assertEqual(len(out["candidates"]), 5)

    def test_excluded_topics_and_duplicates(self):
        cands = [cand(0, candidate_title="이유식 시작 시기 총정리"), cand(1, candidate_title="이유식 시작 시기 총정리"),
                 *[cand(i, candidate_title=f"{WORDS[i]} 완벽 가이드") for i in range(2, 9)]]
        out = run(fake_llm({"candidates": cands}), inp(excluded_topics=["이유식 시작 시기"], candidate_count=10))["output"]
        self.assertTrue(all("이유식" not in c["candidate_title"] for c in out["candidates"]))

    def test_multiple_types_balanced(self):
        cands = [cand(i, "guide") for i in range(5)] + [cand(9, "finance")]
        out = run(fake_llm({"candidates": cands}), inp(requested_content_types=["guide", "finance"]))["output"]
        self.assertIn("finance", [c["content_type"] for c in out["candidates"][:2]])
        self.assertTrue(any(w["code"] == "FINANCE_NO_OFFICIAL_SOURCE" for w in out["warnings"]))

    def test_no_provider_and_no_results(self):
        assert_error(self, td.run(request("topic-discovery", inp(), discovery_run_id="d1"), llm=None, search=None, now=NOW), "AUTH_OR_PERMISSION")
        assert_error(self, run(fake_llm({}), search=fake_search([])), "INSUFFICIENT_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
