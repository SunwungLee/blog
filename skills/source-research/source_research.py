"""source-research: collect sources and evidence summaries for an approved topic."""

import re

from common import ids, privacy
from common.config import role_for
from common.envelope import execute, require_refs
from common.errors import SkillError
from common.facts import numbers
from common.llm import call_json
from common.sources import is_official, run_search
from common.util import invalid, now_iso, require_content_type, require_str, warning

MODULE = "source-research"
SOURCE_TYPES = ("official", "primary", "secondary")
MAX_QUERIES = 4
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")

SYSTEM = (
    "당신은 자료 조사 보조자입니다. 제공된 검색 결과에 실제로 있는 내용만 요약하고 JSON만 출력합니다. "
    "결과에 없는 사실·수치를 추가하지 마세요. 공식·원본 출처를 우선합니다."
)


def _parse(inp):
    topic = inp.get("topic")
    if not isinstance(topic, dict):
        raise invalid("topic 객체가 필요합니다.")
    title = require_str(topic, "title")
    ctype = require_content_type(topic.get("content_type"))
    questions = inp.get("research_questions")
    if not isinstance(questions, list) or not questions or any(not isinstance(q, str) or not q.strip() for q in questions):
        raise invalid("research_questions는 비어 있지 않은 문자열 목록이어야 합니다.")
    criteria = inp.get("source_criteria") or {}
    if not isinstance(criteria, dict):
        raise invalid("source_criteria는 객체여야 합니다.")
    min_sources = criteria.get("min_sources", 3)
    max_sources = criteria.get("max_sources", 8)
    if not (isinstance(min_sources, int) and isinstance(max_sources, int) and 1 <= min_sources <= max_sources <= 15):
        raise invalid("source_criteria의 min_sources/max_sources가 올바르지 않습니다.")
    blocked = inp.get("blocked_terms") or []
    if not isinstance(blocked, list):
        raise invalid("blocked_terms는 문자열 목록이어야 합니다.")
    keyword = topic.get("primary_keyword") if isinstance(topic.get("primary_keyword"), str) else None
    kinds = privacy.scan_values([title, questions, keyword], blocked)
    if kinds:
        raise invalid("식별·민감 정보가 포함되어 있어 검색에 사용할 수 없습니다.", {"kinds": kinds})
    version = inp.get("version_no", 1)
    if not isinstance(version, int) or version < 1:
        raise invalid("version_no는 1 이상의 정수여야 합니다.")
    return title, ctype, [q.strip() for q in questions], min_sources, max_sources, version, keyword


def _prompt(title, questions, results):
    listing = "\n".join(
        f"[S{i}] {r['title']} | {r['publisher']} | {r['published_at'] or '날짜 미상'}\n    {r['snippet']}"
        for i, r in enumerate(results, 1)
    )
    qs = "\n".join(f"Q{i}. {q}" for i, q in enumerate(questions, 1))
    return (
        f"주제: {title}\n조사 질문:\n{qs}\n\n검색 결과:\n{listing}\n\n"
        '출력: {"items":[{"source_ref":"S1","source_type":"official|primary|secondary",'
        '"evidence_summary":"결과에 근거한 1~3문장","answers_questions":["Q1"]}],'
        '"gaps":["답하지 못한 질문"]}'
    )


def _validate(data):
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("items 배열이 필요합니다.")
    return data


def _render(title, items, gaps, stamp):
    lines = [f"# 자료 조사: {title}", "", f"조사 시각: {stamp}", ""]
    for n, it in enumerate(items, 1):
        lines += [f"## {n}. {it['source_title']}", f"- 출처: {it['source_url']}", f"- 발행처: {it['publisher']}",
                  f"- 유형: {it['source_type']} / 게시일: {it['published_at'] or '미상'} / 확인일: {it['accessed_at'][:10]}",
                  f"- 근거 요약: {it['evidence_summary']}", ""]
    if gaps:
        lines += ["## 미확인 질문", *[f"- {g}" for g in gaps], ""]
    return "\n".join(lines)


def research(inp, refs, llm, search, now):
    require_refs(refs, "content_id", "topic_id")
    title, ctype, questions, min_sources, max_sources, version, keyword = _parse(inp)
    stamp = now_iso(now)
    queries = ([f"{title} {keyword}" if keyword else title] + [f"{title} {q}" for q in questions])[:MAX_QUERIES]
    results, seen = [], set()
    for q in queries:
        for r in run_search(search, q):
            if r["url"] not in seen:
                seen.add(r["url"])
                results.append(r)
    if not results:
        raise SkillError("INSUFFICIENT_EVIDENCE", "검색 결과가 없어 자료를 수집할 수 없습니다.")
    data = call_json(llm, role_for("research_synthesis", "high_quality"), SYSTEM, _prompt(title, questions, results), _validate)
    items, used, dropped = [], set(), []
    for raw in data["items"]:
        m = re.fullmatch(r"S(\d+)", str(raw.get("source_ref", ""))) if isinstance(raw, dict) else None
        if not m or not 1 <= int(m.group(1)) <= len(results) or int(m.group(1)) in used:
            continue
        summary = raw.get("evidence_summary")
        if not isinstance(summary, str) or not summary.strip():
            continue
        r = results[int(m.group(1)) - 1]
        invented = numbers(summary) - numbers(f"{r['title']} {r['snippet']}")
        if invented:
            dropped.append(r["url"])
            continue  # a number the search result does not contain would later count as "supported"
        used.add(int(m.group(1)))
        stype = raw.get("source_type") if raw.get("source_type") in SOURCE_TYPES else "secondary"
        if is_official(r["url"]):
            stype = "official"
        elif stype == "official":
            stype = "secondary"  # only the domain check can establish official status
        published = r["published_at"] if isinstance(r["published_at"], str) and _DATE.match(r["published_at"]) else None
        items.append({
            "research_id": ids.new_uuid(), "source_title": r["title"], "source_url": r["url"],
            "publisher": r["publisher"], "published_at": published, "accessed_at": stamp,
            "source_type": stype, "evidence_summary": summary.strip(), "verification_status": "unverified",
        })
    items.sort(key=lambda i: SOURCE_TYPES.index(i["source_type"]))
    items = items[:max_sources]
    if len(items) < min_sources:
        raise SkillError("INSUFFICIENT_EVIDENCE", "요건을 충족하는 출처가 부족합니다.", details={"found": len(items), "required": min_sources})
    warnings = []
    if dropped:
        warnings.append(warning("SUMMARY_NUMBER_NOT_IN_SOURCE", "검색 결과에 없는 수치가 들어간 요약은 제외했습니다.", source_urls=dropped))
    if ctype == "finance" and not any(i["source_type"] == "official" for i in items):
        raise SkillError("INSUFFICIENT_EVIDENCE", "금융·정책 주제는 공식 출처가 필요합니다.")
    if not any(i["source_type"] in ("official", "primary") for i in items):
        warnings.append(warning("NO_PRIMARY_SOURCE", "공식·원본 출처가 없고 2차 출처만 있습니다."))
    gaps = [g.strip() for g in data.get("gaps", []) if isinstance(g, str) and g.strip()] if isinstance(data.get("gaps"), list) else []
    name = ids.file_name(refs["content_id"], "research", version, "md")
    return {
        "sources": items,
        "gaps": gaps,
        "warnings": warnings,
        "artifact": {
            "file_name": name, "drive_path": ids.drive_path(refs["content_id"], "research"),
            "content_type": "text/markdown", "content": _render(title, items, gaps, stamp),
        },
    }


def run(request, *, llm=None, search=None, now=None):
    return execute(request, MODULE, lambda inp, refs: research(inp, refs, llm, search, now))
