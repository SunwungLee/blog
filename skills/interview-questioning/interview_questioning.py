"""interview-questioning: find unanswered/conflicting interview answers, ask 1-3 follow-ups."""

from common import ids, privacy
from common.config import role_for
from common.envelope import execute, require_refs
from common.llm import call_json
from common.util import invalid, require_content_type, similar, warning

MODULE = "interview-questioning"
DONT_KNOW = "모름"
MAX_FOLLOWUPS = 3

SYSTEM = (
    "당신은 인터뷰어입니다. 이미 받은 답변에서 빠졌거나 서로 모순되는 부분만 찾아 JSON으로 출력합니다. "
    "답변을 대신 지어내거나 '모름'으로 답한 항목을 다시 묻지 마세요. 추가 질문은 최대 3개입니다."
)


def _truthy_required(value):
    return value is True or str(value).strip().lower() in ("true", "1", "y", "yes", "필수")


def _version(t):
    try:
        return int(t.get("version", 1))
    except (TypeError, ValueError):
        raise invalid("질문 템플릿 version은 정수여야 합니다.", {"question_id": t.get("question_id")}) from None


def _sort_order(t):
    try:
        return int(t.get("sort_order", 0))
    except (TypeError, ValueError):
        return 0


def _active_templates(templates, ctype):
    latest = {}
    for t in templates:
        if not isinstance(t, dict) or not t.get("question_id") or not t.get("question"):
            raise invalid("질문 템플릿에 question_id와 question이 필요합니다.")
        qid = t["question_id"]
        if qid not in latest or _version(t) > _version(latest[qid]):
            latest[qid] = t
    rows = [t for t in latest.values() if str(t.get("active", True)).lower() not in ("false", "0", "n")
            and t.get("content_type") in (None, "", ctype)]
    return sorted(rows, key=lambda t: (bool(t.get("content_type")), _sort_order(t)))


def _is_answered(answer):
    return isinstance(answer, dict) and isinstance(answer.get("answer_text"), str) and bool(answer["answer_text"].strip())


def _prompt(plan, answered, dont_know, ctype):
    qa = "\n".join(f"Q: {a['question_text']}\nA: {a['shown']}" for a in answered)
    return (
        f"콘텐츠 유형: {ctype}\n기획 경험 질문 주제: {(plan or {}).get('interview_focus', [])}\n"
        f"기획 목차: {[s.get('heading') for s in (plan or {}).get('outline', [])]}\n"
        f"모름으로 답해 다시 묻지 않을 질문: {dont_know}\n\n지금까지의 답변:\n{qa}\n\n"
        '출력: {"conflicts":[{"description":"","question_ids":[""]}],"followups":[{"question":"","reason":""}]}'
    )


def _validate(data):
    if not isinstance(data, dict):
        raise ValueError("객체여야 합니다.")
    return data


def question(inp, refs, llm):
    require_refs(refs, "content_id")
    ctype = require_content_type(inp.get("content_type"))
    templates, answers = inp.get("templates"), inp.get("answers", [])
    if not isinstance(templates, list) or not isinstance(answers, list):
        raise invalid("templates와 answers는 목록이어야 합니다.")
    rows = _active_templates(templates, ctype)
    by_id = {a.get("question_id"): a for a in answers if _is_answered(a)}
    pending_ai = [a for a in answers if isinstance(a, dict) and a.get("question_source") == "ai" and not _is_answered(a)]

    pending = [t for t in rows if t["question_id"] not in by_id]
    missing_required = [t for t in pending if _truthy_required(t.get("required"))]
    result = {
        "pending_questions": [
            {"question_id": t["question_id"], "version": _version(t), "question": t["question"],
             "required": _truthy_required(t.get("required")), "question_source": "template"}
            for t in pending
        ] + [{"question_id": a["question_id"], "question": a.get("question_text", ""), "required": False, "question_source": "ai"} for a in pending_ai],
        "missing_required": [t["question_id"] for t in missing_required],
        "conflicts": [], "followup_questions": [], "warnings": [],
    }
    result["can_advance"] = not missing_required
    if missing_required or pending_ai or not by_id:
        return result
    if llm is None:
        result["warnings"].append(warning("GAP_ANALYSIS_SKIPPED", "AI 공급자가 없어 모순·누락 분석과 추가 질문 생성을 건너뛰었습니다."))
        return result

    blocked = inp.get("blocked_terms") or []
    if not isinstance(blocked, list):
        raise invalid("blocked_terms는 문자열 목록이어야 합니다.")
    asked_text = [t["question"] for t in rows] + [str(a.get("question_text", "")) for a in answers if isinstance(a, dict)]
    dont_know = [str(a.get("question_text", "")) for a in by_id.values() if a["answer_text"].strip() == DONT_KNOW]
    shown = []
    for a in by_id.values():
        text = a["answer_text"].strip()
        if privacy.find_pii(text, blocked):
            result["warnings"].append(warning("PII_IN_ANSWER", "식별 정보가 있어 이 답변은 AI에 보내지 않았습니다.", question_id=a.get("question_id")))
            text = "[개인정보 포함 답변: 내용 생략]"
        shown.append({"question_text": str(a.get("question_text", "")), "shown": text})
    data = call_json(llm, role_for("answer_analysis", "lightweight"), SYSTEM, _prompt(inp.get("plan"), shown, dont_know, ctype), _validate)
    for c in data.get("conflicts", []) if isinstance(data.get("conflicts"), list) else []:
        if isinstance(c, dict) and isinstance(c.get("description"), str) and c["description"].strip():
            known = [q for q in c.get("question_ids", []) if isinstance(q, str) and q in by_id] if isinstance(c.get("question_ids"), list) else []
            result["conflicts"].append({"description": c["description"].strip(), "question_ids": known})
    for f in data.get("followups", []) if isinstance(data.get("followups"), list) else []:
        text = str(f.get("question", "")).strip() if isinstance(f, dict) else ""
        if not text or privacy.find_pii(text, blocked) or any(similar(text, q, 0.7) for q in asked_text + dont_know):
            continue
        asked_text.append(text)
        result["followup_questions"].append({"question_id": ids.new_uuid(), "question": text, "reason": str(f.get("reason", "")).strip(),
                                             "required": False, "question_source": "ai"})
        if len(result["followup_questions"]) == MAX_FOLLOWUPS:
            break
    return result


def run(request, *, llm=None):
    return execute(request, MODULE, lambda inp, refs: question(inp, refs, llm))
