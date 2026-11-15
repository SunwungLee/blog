"""content-planning: direction, outline and key message for an approved topic."""

from common import ids
from common.config import role_for
from common.envelope import execute, require_refs
from common.llm import call_json
from common.util import invalid, now_iso, require_content_type, require_str

MODULE = "content-planning"
FINANCE_NOTICE_HEADING = "유의사항 및 정보 기준일"
SYSTEM = (
    "당신은 한국어 블로그 기획자입니다. 제공된 주제와 조사 자료만으로 기획안을 JSON으로 출력합니다. "
    "작성자의 경험을 지어내지 말고, 경험이 필요한 부분은 interview_focus에 질문 주제로만 적으세요."
)
TYPE_GUIDE = {
    "experience": "독자가 공감할 상황 → 실제 경험(질문으로 확보) → 시행착오 → 배운 점",
    "finance": "개념 → 공식 근거 기반 제도·조건 → 주의점. 매수 추천·수익 예측 금지",
    "review": "구매 배경 → 사용 경험(질문으로 확보) → 장단점 → 추천 대상",
    "guide": "대상·조건 → 단계별 절차 → 자주 하는 실수 → 참고 링크",
    "compare": "비교 기준 → 항목별 비교 → 상황별 선택 가이드",
}


def _parse(inp):
    topic = inp.get("topic")
    if not isinstance(topic, dict):
        raise invalid("topic 객체가 필요합니다.")
    title = require_str(topic, "title")
    ctype = require_content_type(topic.get("content_type"))
    sources = inp.get("research_sources")
    if not isinstance(sources, list) or not sources:
        raise invalid("research_sources가 비어 있습니다.")
    research = {}
    for s in sources:
        if not isinstance(s, dict) or not isinstance(s.get("research_id"), str) or not s["research_id"] or not isinstance(s.get("evidence_summary"), str) or not s["evidence_summary"].strip():
            raise invalid("research_sources 항목에 research_id와 evidence_summary가 필요합니다.")
        research[s["research_id"]] = s
    version = inp.get("version_no", 1)
    if not isinstance(version, int) or version < 1:
        raise invalid("version_no는 1 이상의 정수여야 합니다.")
    return title, ctype, topic, research, version, inp.get("revision_feedback")


def _prompt(title, ctype, topic, research, feedback):
    src = "\n".join(f"- {rid}: {s.get('source_title', '')} — {s['evidence_summary']}" for rid, s in research.items())
    return (
        f"제목 후보: {title}\n유형: {ctype} ({TYPE_GUIDE[ctype]})\n대표 키워드: {topic.get('primary_keyword', '')}\n"
        f"연관 키워드: {topic.get('related_keywords', [])}\n검색 의도: {topic.get('search_intent', '')}\n"
        f"조사 자료:\n{src}\n" + (f"이전 기획안에 대한 수정 요청: {feedback}\n" if feedback else "")
        + '\n출력: {"working_title":"","direction":"","key_message":"","target_reader":"",'
        '"outline":[{"heading":"","points":[""],"research_ids":[""]}],"interview_focus":["경험 질문 주제"],'
        '"comparison_criteria":["compare 유형만"]}'
    )


def _make_validator(ctype, research):
    def validate(data):
        if not isinstance(data, dict):
            raise ValueError("객체여야 합니다.")
        for key in ("working_title", "direction", "key_message"):
            if not isinstance(data.get(key), str) or not data[key].strip():
                raise ValueError(f"{key}가 필요합니다.")
        outline = data.get("outline")
        if not isinstance(outline, list) or not 3 <= len(outline) <= 10:
            raise ValueError("outline은 3~10개 섹션이어야 합니다.")
        for sec in outline:
            if not isinstance(sec, dict) or not isinstance(sec.get("heading"), str) or not sec["heading"].strip():
                raise ValueError("각 섹션에 heading이 필요합니다.")
            if not isinstance(sec.get("points"), list) or not any(isinstance(p, str) and p.strip() for p in sec["points"]):
                raise ValueError("각 섹션에 points가 필요합니다.")
            rids = sec.get("research_ids", [])
            if rids is None:
                rids = sec["research_ids"] = []
            if not isinstance(rids, list) or any(not isinstance(r, str) for r in rids):
                raise ValueError("research_ids는 문자열 배열이어야 합니다.")
            unknown = [r for r in rids if r not in research]
            if unknown:
                raise ValueError(f"존재하지 않는 research_id: {unknown}")
        focus = data.get("interview_focus", [])
        if focus is not None and not isinstance(focus, list):
            raise ValueError("interview_focus는 배열이어야 합니다.")
        if ctype in ("experience", "review") and (not isinstance(focus, list) or len(focus) < 2):
            raise ValueError("experience/review 유형은 interview_focus가 2개 이상 필요합니다.")
        criteria = data.get("comparison_criteria", [])
        if criteria is not None and not isinstance(criteria, list):
            raise ValueError("comparison_criteria는 배열이어야 합니다.")
        if ctype == "compare" and (not isinstance(criteria, list) or len(criteria) < 3):
            raise ValueError("compare 유형은 comparison_criteria가 3개 이상 필요합니다.")
        return data
    return validate


def _render(plan, ctype, stamp):
    lines = [f"# 기획안: {plan['working_title']}", "", f"- 유형: {ctype}", f"- 작성: {stamp}", f"- 독자: {plan.get('target_reader', '')}",
             "", "## 방향", plan["direction"], "", "## 핵심 메시지", plan["key_message"], "", "## 목차"]
    for n, sec in enumerate(plan["outline"], 1):
        lines.append(f"{n}. **{sec['heading']}**")
        lines += [f"   - {p}" for p in sec["points"]]
    if plan["interview_focus"]:
        lines += ["", "## 사용자 경험 질문 주제", *[f"- {f}" for f in plan["interview_focus"]]]
    if plan.get("comparison_criteria"):
        lines += ["", "## 비교 기준", *[f"- {c}" for c in plan["comparison_criteria"]]]
    return "\n".join(lines) + "\n"


def plan_content(inp, refs, llm, now):
    require_refs(refs, "content_id", "topic_id")
    title, ctype, topic, research, version, feedback = _parse(inp)
    validate = _make_validator(ctype, research)
    data = call_json(llm, role_for("content_planning", "high_quality"), SYSTEM, _prompt(title, ctype, topic, research, feedback), validate)
    outline = [{"heading": s["heading"].strip(), "points": [p.strip() for p in s["points"] if isinstance(p, str) and p.strip()],
                "research_ids": list(dict.fromkeys(s.get("research_ids") or []))} for s in data["outline"]]
    if ctype == "finance" and not any(k in s["heading"] for s in outline for k in ("유의", "면책", "기준일")):
        outline.append({"heading": FINANCE_NOTICE_HEADING, "research_ids": [],
                        "points": ["투자 권유가 아닌 정보 제공임을 명시", "정보 기준일 표기"]})
    plan = {
        "working_title": data["working_title"].strip(), "direction": data["direction"].strip(),
        "key_message": data["key_message"].strip(), "target_reader": str(data.get("target_reader") or "").strip(),
        "outline": outline,
        "interview_focus": [f.strip() for f in data.get("interview_focus") or [] if isinstance(f, str) and f.strip()],
        "comparison_criteria": [c.strip() for c in data.get("comparison_criteria") or [] if isinstance(c, str) and c.strip()] if ctype == "compare" else [],
        "requires_finance_notice": ctype == "finance",
    }
    return {
        "plan": plan,
        "artifact": {
            "file_name": ids.file_name(refs["content_id"], "plan", version, "md"),
            "drive_path": ids.drive_path(refs["content_id"], "plan"),
            "content_type": "text/markdown", "content": _render(plan, ctype, now_iso(now)),
        },
    }


def run(request, *, llm=None, now=None):
    return execute(request, MODULE, lambda inp, refs: plan_content(inp, refs, llm, now))
