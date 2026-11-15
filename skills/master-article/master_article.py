"""master-article: write the Master Article from approved plan, evidence and answers."""

import re

from common import ids, privacy, rules
from common.envelope import execute, require_refs
from common.errors import SkillError
from common.config import quality, role_for, style_prompt
from common.llm import call_json, run_with_quality
from common.util import FIRST_PERSON, invalid, now_iso, require_content_type, warning

MODULE = "master-article"
DONT_KNOW = "모름"
MIN_CHARS = quality("min_body_chars", 1500)
BANNED_FINANCE = rules.BANNED_FINANCE
FINANCE_NOTICE = rules.FINANCE_NOTICE
SPONSOR_NOTICE = rules.SPONSOR_NOTICE

SYSTEM = (
    "당신은 한국어 블로그 작가입니다. 승인된 기획, 조사 자료, 사용자 답변에 있는 내용만 사용해 글을 쓰고 JSON만 출력합니다. "
    "자료에 없는 수치·사실·경험을 지어내지 마세요. 사용자가 '모름'으로 답한 내용은 채워 넣지 말고 생략하세요. "
    "경험 서술은 제공된 답변 범위 안에서만 하세요. 본문은 Markdown입니다."
)


def _parse(inp):
    ctype = require_content_type(inp.get("content_type"))
    plan = inp.get("plan")
    if not isinstance(plan, dict) or not isinstance(plan.get("outline"), list) or not plan["outline"]:
        raise invalid("승인된 plan(outline 포함)이 필요합니다.")
    if any(not isinstance(s, dict) or not isinstance(s.get("heading"), str) or not s["heading"].strip() for s in plan["outline"]):
        raise invalid("plan.outline의 각 항목에 heading이 필요합니다.")
    sources = inp.get("research_sources")
    if not isinstance(sources, list) or not sources:
        raise SkillError("INSUFFICIENT_EVIDENCE", "조사 근거가 없어 원고를 쓸 수 없습니다.")
    research = {s["research_id"]: s for s in sources if isinstance(s, dict) and isinstance(s.get("research_id"), str) and s["research_id"]}
    raw_answers = inp.get("answers", [])
    if not isinstance(raw_answers, list):
        raise invalid("answers는 목록이어야 합니다.")
    answers = [a for a in raw_answers if isinstance(a, dict) and isinstance(a.get("answer_text"), str) and a["answer_text"].strip()]
    usable = [a for a in answers if a["answer_text"].strip() != DONT_KNOW]
    if ctype in ("experience", "review") and not usable:
        raise SkillError("INSUFFICIENT_EVIDENCE", "경험 답변이 없어 경험 기반 원고를 쓸 수 없습니다.")
    version = inp.get("version_no", 1)
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise invalid("version_no는 1 이상의 정수여야 합니다.")
    blocked = inp.get("blocked_terms") or []
    if not isinstance(blocked, list):
        raise invalid("blocked_terms는 문자열 목록이어야 합니다.")
    return ctype, plan, research, answers, usable, version, blocked


def _shown_answers(answers, blocked, warnings):
    """Mask identifying data in answers before they are put into a prompt."""
    shown = []
    for a in answers:
        text, kinds = privacy.redact(a["answer_text"].strip(), blocked)
        if kinds:
            warnings.append(warning("PII_REDACTED", "답변의 식별 정보를 가리고 AI에 보냈습니다.", question_id=a.get("question_id"), kinds=kinds))
        shown.append({"question_text": str(a.get("question_text", "")), "answer_text": text})
    return shown


def _prompt(ctype, plan, research, answers, inp, problems):
    outline = "\n".join(f"{i}. {s['heading']}: {'; '.join(str(p) for p in (s.get('points') if isinstance(s.get('points'), list) else []))}"
                        for i, s in enumerate(plan["outline"], 1))
    src = "\n".join(f"- {rid}: {s.get('source_title', '')} — {s.get('evidence_summary', '')}" for rid, s in research.items())
    qa = "\n".join(f"Q: {a.get('question_text', '')}\nA: {a['answer_text']}" for a in answers) or "없음"
    return (
        f"유형: {ctype}\n작성 방향: {plan.get('direction', '')}\n핵심 메시지: {plan.get('key_message', '')}\n"
        f"목차(각 heading을 '##' 소제목으로 그대로 사용):\n{outline}\n\n조사 자료:\n{src}\n\n사용자 답변:\n{qa}\n"
        f"{style_prompt(inp.get('writing_style'))}\n"
        + (f"사실 검증/검토에서 지적된 사항: {inp['revision_feedback']}\n" if inp.get("revision_feedback") else "")
        + (f"이전 결과의 문제점(반드시 고칠 것): {problems}\n" if problems else "")
        + '\n출력: {"title":"","body_markdown":"","used_research_ids":[""],"warnings":[""]}'
    )


def _validate_shape(data):
    if not isinstance(data, dict):
        raise ValueError("객체여야 합니다.")
    for key in ("title", "body_markdown"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"{key}가 필요합니다.")
    used = data.get("used_research_ids", [])
    if not isinstance(used, list) or any(not isinstance(r, str) for r in used):
        raise ValueError("used_research_ids는 문자열 배열이어야 합니다.")
    if not isinstance(data.get("warnings", []), list):
        data["warnings"] = []
    return data


def _problems(data, ctype, plan, research, has_experience, blocked):
    body = data["body_markdown"]
    out = []
    if len(re.sub(r"\s", "", body)) < MIN_CHARS:
        out.append(f"본문이 {MIN_CHARS}자 미만입니다.")
    missing = [s["heading"] for s in plan["outline"] if s["heading"] not in body]
    if missing:
        out.append(f"목차 소제목 누락: {missing}")
    unknown = [r for r in data.get("used_research_ids", []) if r not in research]
    if unknown:
        out.append(f"존재하지 않는 research_id 사용: {unknown}")
    if not data.get("used_research_ids"):
        out.append("근거(used_research_ids)가 없습니다.")
    if not has_experience and FIRST_PERSON.search(body):
        out.append("제공되지 않은 실제 경험을 단정하는 표현이 있습니다.")
    out += rules.content_problems([data["title"], body], ctype, blocked)
    return out


def _info_date(data, research, inp, stamp):
    """Information reference date: explicit input, else newest access date of the cited sources."""
    given = inp.get("information_as_of")
    if isinstance(given, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", given):
        return given
    dates = [str(research[r].get("accessed_at", ""))[:10] for r in data["used_research_ids"] if r in research]
    dates = [d for d in dates if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d)]
    return max(dates) if dates else stamp[:10]


def _finalize(data, ctype, research, inp, stamp):
    body = data["body_markdown"].rstrip()
    if ctype == "finance":
        if FINANCE_NOTICE not in body:
            body += f"\n\n> {FINANCE_NOTICE}"
        if not rules.INFO_DATE_LINE.search(body):
            body += f"\n> 정보 기준일: {_info_date(data, research, inp, stamp)}"
    if inp.get("sponsored") is True and SPONSOR_NOTICE not in body:
        body = f"> {SPONSOR_NOTICE}\n\n" + body
    used = [research[r] for r in dict.fromkeys(data["used_research_ids"])]
    refs = "\n".join(f"- [{s.get('source_title', s.get('source_url', ''))}]({s['source_url']})" for s in used if s.get("source_url"))
    if refs:
        body += f"\n\n## 참고 자료\n{refs}"
    return body + "\n"


def write(inp, refs, llm, now):
    require_refs(refs, "content_id")
    ctype, plan, research, answers, usable, version, blocked = _parse(inp)
    warnings = []
    shown = _shown_answers(answers, blocked, warnings)

    def produce(problems):
        prompt = _prompt(ctype, plan, research, shown, inp, problems)
        return call_json(llm, role_for("master_article", "high_quality"), SYSTEM, prompt, _validate_shape)

    data = run_with_quality(produce, lambda d: _problems(d, ctype, plan, research, bool(usable), blocked))
    stamp = now_iso(now)
    warnings += [warning("MODEL_WARNING", w) for w in data.get("warnings", []) if isinstance(w, str) and w.strip()]
    skipped = [a.get("question_text", "") for a in answers if a["answer_text"].strip() == DONT_KNOW]
    if skipped:
        warnings.append(warning("DONT_KNOW_OMITTED", "'모름' 답변 항목은 원고에서 채우지 않았습니다.", questions=skipped))
    return {
        "title": data["title"].strip(),
        "used_research_ids": list(dict.fromkeys(data["used_research_ids"])),
        "warnings": warnings,
        "artifact": {
            "file_name": ids.file_name(refs["content_id"], "master", version, "md"),
            "drive_path": ids.drive_path(refs["content_id"], "master"),
            "content_type": "text/markdown", "content": _finalize(data, ctype, research, inp, stamp),
        },
    }


def run(request, *, llm=None, now=None):
    return execute(request, MODULE, lambda inp, refs: write(inp, refs, llm, now))
