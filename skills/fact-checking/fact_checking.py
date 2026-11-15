"""fact-checking: claim-level support check of an article against collected evidence."""

import re

from common import ids
from common.config import quality, role_for
from common.envelope import execute, require_refs
from common.errors import SkillError
from common.llm import call_json
from common.util import invalid, normalize_text, now_iso, require_content_type, require_str, similar

MODULE = "fact-checking"
RESULTS = ("supported", "unsupported", "contradicted", "unverifiable")
DEFAULT_MAX_UNVERIFIED = 0.3
FINANCE_MAX_UNVERIFIED = 0.1
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_NUMERIC_CLAIM = re.compile(r"\d[\d,.]*\s*(?:%|퍼센트|원|만원|억|조|년|개월|일|세|명|배|건|회)")

SYSTEM = (
    "당신은 사실 검토자입니다. 원고의 사실 주장을 추출해 제공된 조사 근거로 확인하고 JSON만 출력합니다. "
    "근거에 직접 나온 경우에만 supported, 근거와 반대면 contradicted, 근거에 없으면 unsupported, "
    "판단 불가는 unverifiable로 하세요. 근거를 추측하지 마세요."
)


def _parse(inp):
    article = require_str(inp, "article_markdown")
    ctype = require_content_type(inp.get("content_type"))
    sources = inp.get("research_sources")
    if not isinstance(sources, list) or not sources:
        raise SkillError("INSUFFICIENT_EVIDENCE", "대조할 조사 근거가 없습니다.")
    research = {s["research_id"]: s for s in sources if isinstance(s, dict) and isinstance(s.get("research_id"), str) and s["research_id"]}
    if not research:
        raise invalid("research_sources에 research_id가 필요합니다.")
    version = inp.get("article_version_id")
    if not isinstance(version, str) or not version.strip():
        raise invalid("article_version_id가 필요합니다(Fact Checks 시트 연결용).")
    return article, ctype, research, version.strip(), inp.get("max_unverified_ratio")


def _prompt(article, research):
    ev = "\n".join(f"[{rid}] {s.get('source_title', '')}: {s.get('evidence_summary', '')}" for rid, s in research.items())
    return (
        f"원고:\n{article}\n\n조사 근거:\n{ev}\n\n"
        '출력: {"claims":[{"claim_text":"원고 문장 그대로","result":"supported|unsupported|contradicted|unverifiable",'
        '"research_id":"근거 ID 또는 null","note":""}]}'
    )


def _validate(data):
    if not isinstance(data, dict) or not isinstance(data.get("claims"), list):
        raise ValueError("claims 배열이 필요합니다.")
    return data


def _numbers(text):
    return {n.replace(",", "") for n in _NUMBER.findall(text)}


def _sentences(article):
    body = article.split("## 참고 자료")[0]
    body = re.sub(r"^#{1,6}.*$", "", body, flags=re.M)
    return [s.strip() for s in re.split(r"(?<=[.!?。])\s+|\n+", body) if s.strip()]


def check(inp, refs, llm, now, run_id=None):
    require_refs(refs, "content_id")
    article, ctype, research, article_version_id, max_ratio = _parse(inp)
    if max_ratio is None:
        limits = quality("max_unverified_ratio", {})
        limits = limits if isinstance(limits, dict) else {}
        max_ratio = limits.get("finance", FINANCE_MAX_UNVERIFIED) if ctype == "finance" else limits.get("default", DEFAULT_MAX_UNVERIFIED)
    if isinstance(max_ratio, bool) or not isinstance(max_ratio, (int, float)) or not 0 <= max_ratio <= 1:
        raise invalid("max_unverified_ratio는 0~1 사이여야 합니다.")
    data = call_json(llm, role_for("fact_checking", "high_quality"), SYSTEM, _prompt(article, research), _validate)
    norm_article = normalize_text(article)
    stamp = now_iso(now)
    claims, covered = [], []
    for raw in data["claims"]:
        if not isinstance(raw, dict):
            continue
        text = str(raw.get("claim_text", "")).strip()
        if not text or (normalize_text(text) not in norm_article and not any(similar(text, s, 0.75) for s in _sentences(article))):
            continue  # not actually in the article
        result = raw.get("result") if isinstance(raw.get("result"), str) and raw.get("result") in RESULTS else "unverifiable"
        rid = raw.get("research_id") if isinstance(raw.get("research_id"), str) and raw.get("research_id") in research else None
        note = str(raw.get("note", "") or "").strip()
        if result in ("supported", "contradicted") and rid is None:
            result, note = "unverifiable", (note + " 유효한 근거 ID가 없어 확인 불가로 처리").strip()
        if result == "supported":
            if _numbers(text) - _numbers(str(research[rid].get("evidence_summary", ""))):
                result, note = "unverifiable", (note + " 주장의 수치가 근거 요약에 없음").strip()
            elif ctype == "finance" and research[rid].get("source_type") != "official":
                result, note = "unverifiable", (note + " 금융 주장은 공식 출처 근거가 필요").strip()
        claims.append({"claim_text": text, "result": result, "research_id": rid, "note": note})
        covered.append(text)
    for s in _sentences(article):
        if _NUMERIC_CLAIM.search(s) and not any(similar(s, c, 0.7) for c in covered):
            claims.append({"claim_text": s, "result": "unverifiable", "research_id": None, "note": "수치 주장이 검토 목록에서 누락되어 확인 불가로 추가"})
    if not claims:
        raise SkillError("INSUFFICIENT_EVIDENCE", "검토할 사실 주장을 찾지 못했습니다.")
    for c in claims:
        c.update({"fact_check_id": ids.new_uuid(), "content_id": refs["content_id"],
                  "article_version_id": article_version_id, "checked_at": stamp, "created_by_run_id": run_id})
    counts = {r: sum(1 for c in claims if c["result"] == r) for r in RESULTS}
    unresolved = [c for c in claims if c["result"] != "supported"]
    ratio = (counts["unverifiable"] + counts["unsupported"]) / len(claims)
    reasons = []
    if counts["contradicted"]:
        reasons.append("근거와 모순되는 주장이 있습니다.")
    if counts["unsupported"]:
        reasons.append("근거 없는 주장이 있습니다.")
    if ratio > max_ratio:
        reasons.append(f"확인하지 못한 주장 비율 {ratio:.0%}가 한도 {max_ratio:.0%}를 넘었습니다.")
    return {"passed": not reasons, "reasons": reasons, "counts": counts, "claims": claims, "unresolved_claims": unresolved}


def run(request, *, llm=None, now=None):
    run_id = request.get("run_id") if isinstance(request, dict) else None
    return execute(request, MODULE, lambda inp, refs: check(inp, refs, llm, now, run_id))
