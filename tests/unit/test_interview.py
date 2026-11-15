import unittest

import helpers
from helpers import CID, assert_error, fake_llm, request
from common.loader import load_skill

iq = load_skill("interview-questioning")

TEMPLATES = [
    {"question_id": "c1", "category": "배경", "content_type": "", "question": "어떤 계기로 시작했나요?", "required": True, "sort_order": 1, "active": True, "version": 1},
    {"question_id": "c1", "category": "배경", "content_type": "", "question": "시작한 계기를 알려주세요", "required": True, "sort_order": 1, "active": True, "version": 2},
    {"question_id": "e1", "category": "경험", "content_type": "experience", "question": "가장 힘들었던 순간은?", "required": True, "sort_order": 1, "active": True, "version": 1},
    {"question_id": "e2", "category": "경험", "content_type": "experience", "question": "다시 한다면 바꿀 점은?", "required": False, "sort_order": 2, "active": True, "version": 1},
    {"question_id": "g1", "category": "가이드", "content_type": "guide", "question": "절차는?", "required": True, "sort_order": 1, "active": True, "version": 1},
    {"question_id": "x1", "category": "기타", "content_type": "", "question": "비활성 질문", "required": True, "sort_order": 9, "active": False, "version": 1},
]


def ans(qid, text, q="질문", source="template"):
    return {"question_id": qid, "question_text": q, "answer_text": text, "question_source": source}


def go(inp, llm=None):
    return iq.run(request("interview-questioning", inp, content_id=CID), llm=llm)


class InterviewTests(unittest.TestCase):
    def test_blocks_while_required_missing(self):
        out = go({"content_type": "experience", "templates": TEMPLATES, "answers": []})["output"]
        self.assertEqual(out["missing_required"], ["c1", "e1"])
        self.assertFalse(out["can_advance"])
        self.assertEqual([q["question_id"] for q in out["pending_questions"]], ["c1", "e1", "e2"])
        self.assertEqual(out["pending_questions"][0]["version"], 2)  # latest version only

    def test_dont_know_counts_as_answered(self):
        out = go({"content_type": "experience", "templates": TEMPLATES, "answers": [ans("c1", "모름"), ans("e1", "밤샘")]})["output"]
        self.assertTrue(out["can_advance"])
        self.assertEqual([q["question_id"] for q in out["pending_questions"]], ["e2"])  # optional stays pending

    def test_type_filtering(self):
        out = go({"content_type": "guide", "templates": TEMPLATES, "answers": []})["output"]
        self.assertEqual(out["missing_required"], ["c1", "g1"])

    def test_followups_limited_filtered_and_idempotent_ids(self):
        llm = fake_llm({"conflicts": [{"description": "기간이 서로 다름", "question_ids": ["c1", "nope"]}],
                        "followups": [{"question": "그때 가장 도움이 된 것은 무엇이었나요?", "reason": "빈틈"},
                                      {"question": "가장 힘들었던 순간은 언제였나요?", "reason": "중복"},
                                      {"question": "비용은 얼마나 들었나요?"}, {"question": "기간은 얼마나 걸렸나요?"},
                                      {"question": "누구와 함께 했나요?"}]})
        inp = {"content_type": "experience", "templates": TEMPLATES, "answers": [ans("c1", "친구 추천", "시작한 계기를 알려주세요"), ans("e1", "밤샘", "가장 힘들었던 순간은?")]}
        out = go(inp, llm)["output"]
        qs = [f["question"] for f in out["followup_questions"]]
        self.assertEqual(len(qs), 3)
        self.assertNotIn("가장 힘들었던 순간은 언제였나요?", qs)
        self.assertEqual(out["conflicts"][0]["question_ids"], ["c1"])
        self.assertTrue(all(f["question_source"] == "ai" and len(f["question_id"]) == 36 for f in out["followup_questions"]))

    def test_no_llm_call_when_required_missing_or_dont_know_not_reasked(self):
        llm = fake_llm({"conflicts": [], "followups": [{"question": "절차는?"}]})
        go({"content_type": "experience", "templates": TEMPLATES, "answers": [ans("c1", "a")]}, llm)
        self.assertEqual(llm.calls, [])
        out = go({"content_type": "guide", "templates": TEMPLATES, "answers": [ans("c1", "a", "시작한 계기를 알려주세요"), ans("g1", "모름", "절차는?")]}, llm)["output"]
        self.assertEqual(out["followup_questions"], [])  # near-duplicate of a "모름" question is not re-asked

    def test_pii_answers_not_sent_to_ai(self):
        llm = fake_llm({"conflicts": [], "followups": []})
        out = go({"content_type": "guide", "templates": TEMPLATES, "answers": [ans("c1", "연락처 010-1234-5678"), ans("g1", "신청")]}, llm)["output"]
        self.assertNotIn("010-1234-5678", llm.calls[0][1])
        self.assertEqual(out["warnings"][0]["code"], "PII_IN_ANSWER")

    def test_invalid_input(self):
        assert_error(self, go({"content_type": "bad", "templates": [], "answers": []}), "INVALID_INPUT")
        assert_error(self, go({"content_type": "guide", "templates": [{"x": 1}], "answers": []}), "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
