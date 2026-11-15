"""topic-discovery: ranked Korean blog topic candidates backed by search sources."""

import re
from datetime import date

from common import privacy
from common.config import role_for
from common.envelope import execute, require_refs
from common.errors import SkillError
from common.llm import call_json
from common.sources import is_official, run_search
from common.util import (
    CONTENT_TYPES, FIRST_PERSON, TYPE_LABELS, invalid, now_iso, similar, warning,
)

MODULE = "topic-discovery"
FRESHNESS = ("evergreen", "seasonal", "timely")
MIN_CANDIDATES, MAX_CANDIDATES, DEFAULT_CANDIDATES = 5, 10, 5
MAX_SEARCH_REQUESTS = 2
SUPPORTED_LOCALES = ("ko-KR",)
_MEASURED = re.compile(r"(검색량|경쟁도|조회수|트렌드 순위)\s*[:은는이가]?\s*\d")

SYSTEM = (
    "당신은 한국어 블로그 편집자입니다. 제공된 검색 결과만 근거로 주제 후보를 제안하고 JSON만 출력합니다. "
    "검색량·경쟁도·순위 수치를 만들어 내지 말고, 작성자의 실제 경험을 지어내지 마세요. "
    "경험담(experience) 주제는 '실제 경험이 있을 때 작성 가능'한 형태로 제안하세요."
)


def _parse_input(inp):
    context = inp.get("editorial_context")
    if not isinstance(context, str) or not context.strip():
        raise invalid("editorial_context가 필요합니다.")
    active = inp.get("active_content_types")
    if not isinstance(active, list) or not active or any(t not in CONTENT_TYPES for t in active):
        raise invalid("active_content_types는 유효한 콘텐츠 유형 목록이어야 합니다.")
    requested = inp.get("requested_content_types") or list(active)
    if not isinstance(requested, list) or any(t not in active for t in requested):
        raise invalid("requested_content_types는 활성 유형의 부분집합이어야 합니다.")
    count = inp.get("candidate_count", DEFAULT_CANDIDATES)
    if isinstance(count, bool) or not isinstance(count, int) or not MIN_CANDIDATES <= count <= MAX_CANDIDATES:
        raise invalid("candidate_count는 5~10 정수여야 합니다.")
    excluded = inp.get("excluded_topics") or []
    if not isinstance(excluded, list) or any(not isinstance(x, str) for x in excluded):
        raise invalid("excluded_topics는 문자열 목록이어야 합니다.")
    criteria = inp.get("discovery_criteria") or ""
    if not isinstance(criteria, str):
        raise invalid("discovery_criteria는 문자열이어야 합니다.")
    locale = inp.get("locale", "ko-KR")
    if locale not in SUPPORTED_LOCALES:
        raise invalid("locale은 현재 ko-KR만 지원합니다.", {"supported": list(SUPPORTED_LOCALES)})
    blocked = inp.get("blocked_terms") or []
    kinds = privacy.scan_values([context, criteria, excluded], blocked)
    if kinds:
        raise invalid("식별·민감 정보가 포함되어 있어 검색에 사용할 수 없습니다.", {"kinds": kinds})
    return {
        "context": context.strip(), "criteria": criteria.strip(),
        "requested": list(dict.fromkeys(requested)), "count": count,
        "excluded": [x.strip() for x in excluded if x.strip()],
        "locale": locale,
    }


def _queries(p, today):
    labels = " ".join(TYPE_LABELS[t] for t in p["requested"])
    focus = f"{p['context']} {p['criteria']}".strip()
    return [f"{focus} {labels} 블로그 주제", f"{focus} {today.year}년 최신 이슈 공식 자료"][:MAX_SEARCH_REQUESTS]


def _prompt(p, results):
    listing = "\n".join(f"[S{i}] {r['title']} ({r['publisher']}) {r['snippet']}" for i, r in enumerate(results, 1))
    return (
        f"블로그 맥락: {p['context']}\n발굴 기준: {p['criteria'] or '없음'}\n"
        f"요청 유형: {', '.join(p['requested'])}\n제외할 주제: {p['excluded'] or '없음'}\n"
        f"필요 후보 수: {p['count']} (근거가 부족하면 더 적게)\n\n검색 결과:\n{listing}\n\n"
        '출력 형식: {"candidates":[{"content_type":"","candidate_title":"","primary_keyword":"",'
        '"related_keywords":["3~5개"],"search_intent":"","rationale":"","freshness":"evergreen|seasonal|timely",'
        '"source_refs":["S1"]}]} 추천 순서대로 정렬하세요. ID와 점수는 만들지 마세요.'
    )


def _validate_shape(data):
    if not isinstance(data, dict) or not isinstance(data.get("candidates"), list):
        raise ValueError("candidates 배열이 필요합니다.")
    return data["candidates"]


def _clean_candidate(raw, p, results, now):
    """Return (candidate, None) or (None, reason)."""
    if not isinstance(raw, dict):
        return None, "not_object"
    ctype = raw.get("content_type")
    if ctype not in p["requested"]:
        return None, "content_type"
    texts = {k: raw.get(k) for k in ("candidate_title", "primary_keyword", "search_intent", "rationale")}
    if any(not isinstance(v, str) or not v.strip() for v in texts.values()):
        return None, "missing_text"
    related = raw.get("related_keywords")
    if not isinstance(related, list) or any(not isinstance(k, str) or not k.strip() for k in related):
        return None, "related_keywords"
    primary = texts["primary_keyword"].strip()
    related = [k for k in dict.fromkeys(k.strip() for k in related) if k != primary]
    if not 3 <= len(related) <= 5:
        return None, "related_keywords"
    if raw.get("freshness") not in FRESHNESS:
        return None, "freshness"
    if FIRST_PERSON.search(texts["candidate_title"]):
        return None, "claims_experience"
    if any(_MEASURED.search(v) for v in texts.values()):
        return None, "measured_claim"
    refs = raw.get("source_refs")
    sources, seen = [], set()
    for ref in refs if isinstance(refs, list) else []:
        m = re.fullmatch(r"S(\d+)", str(ref))
        if m and 1 <= int(m.group(1)) <= len(results) and int(m.group(1)) not in seen:
            seen.add(int(m.group(1)))
            r = results[int(m.group(1)) - 1]
            sources.append({"title": r["title"], "url": r["url"], "publisher": r["publisher"], "accessed_at": now})
    if not sources:
        return None, "no_source"
    return {
        "content_type": ctype,
        "candidate_title": texts["candidate_title"].strip(),
        "primary_keyword": primary,
        "related_keywords": related,
        "search_intent": texts["search_intent"].strip(),
        "rationale": texts["rationale"].strip(),
        "freshness": raw["freshness"],
        "requires_firsthand_experience": ctype in ("experience", "review"),
        "sources": sources,
    }, None


def _select(candidates, p):
    kept = []
    for c in candidates:
        if any(similar(c["candidate_title"], e) for e in p["excluded"]):
            continue
        if any(similar(c["candidate_title"], k["candidate_title"], 0.85) for k in kept):
            continue
        kept.append(c)
    # one best candidate per requested type first, then the rest in model order
    first, seen = [], set()
    for c in kept:
        if c["content_type"] not in seen:
            seen.add(c["content_type"])
            first.append(c)
    ordered = first + [c for c in kept if c not in first] if len(p["requested"]) > 1 else kept
    return ordered[: p["count"]]


def discover(inp, refs, llm, search, now, today):
    require_refs(refs, "discovery_run_id")
    p = _parse_input(inp)
    stamp = now_iso(now)
    results, seen = [], set()
    for query in _queries(p, today):
        for r in run_search(search, query):
            if r["url"] not in seen:
                seen.add(r["url"])
                results.append(r)
    if not results:
        raise SkillError("INSUFFICIENT_EVIDENCE", "사용할 수 있는 검색 근거가 없습니다.")
    raw = call_json(llm, role_for("topic_discovery", "high_quality"), SYSTEM, _prompt(p, results), _validate_shape)
    candidates = [c for c, _ in (_clean_candidate(r, p, results, stamp) for r in raw) if c]
    selected = _select(candidates, p)
    if len(selected) < MIN_CANDIDATES:
        raise SkillError(
            "INSUFFICIENT_EVIDENCE", "근거를 갖춘 후보가 5개 미만입니다.",
            details={"supported_candidates": len(selected)},
        )
    warnings = []
    if len(selected) < p["count"]:
        warnings.append(warning("REQUESTED_COUNT_NOT_MET", f"요청 {p['count']}개 중 {len(selected)}개만 근거를 갖췄습니다."))
    for c in selected:
        if c["content_type"] == "finance" and not any(is_official(s["url"]) for s in c["sources"]):
            warnings.append(warning("FINANCE_NO_OFFICIAL_SOURCE", "금융 후보에 공식 출처가 없습니다.", candidate_title=c["candidate_title"]))
    return {"candidates": selected, "warnings": warnings}


def run(request, *, llm=None, search=None, now=None, today=None):
    return execute(request, MODULE, lambda inp, refs: discover(inp, refs, llm, search, now, today or date.today()))
