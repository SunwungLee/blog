"""performance-analysis: aggregate collected metrics deterministically; AI only adds suggestions."""

from collections import defaultdict
from datetime import datetime
from statistics import mean

from common.config import quality, role_for
from common.envelope import execute, require_refs
from common.llm import call_json
from common.util import invalid, warning

MODULE = "performance-analysis"
KNOWN_METRICS = ("views", "visitors", "likes", "comments", "avg_read_seconds", "bounce_rate")
LOW_ENGAGEMENT = quality("low_engagement_ratio", 0.005)  # (likes + comments) / views
EARLY_DAYS = quality("early_period_days", 7)

SYSTEM = (
    "당신은 블로그 성과 분석가입니다. 제공된 집계 수치만 근거로 개선 제안을 JSON으로 출력합니다. "
    "수치를 지어내거나 인과를 단정하지 말고 '가설'로 표현하세요."
)


def _parse(inp):
    metrics = inp.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise invalid("metrics는 비어 있지 않은 목록이어야 합니다.")
    rows = []
    for m in metrics:
        if not isinstance(m, dict) or m.get("platform") not in ("naver", "blogspot"):
            raise invalid("metric에는 platform(naver|blogspot)이 필요합니다.")
        if not isinstance(m.get("metric_name"), str) or not m["metric_name"].strip() or not m.get("measured_at"):
            raise invalid("metric에는 metric_name과 measured_at이 필요합니다.")
        value = m.get("metric_value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise invalid("metric_value는 0 이상의 숫자여야 합니다.")
        rows.append({**m, "_at": _parse_time(m.get("measured_at"))})
    return rows


def _parse_publishing(inp):
    raw = inp.get("publishing")
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise invalid("publishing은 목록이어야 합니다.")
    published = {}
    for p in raw:
        if not isinstance(p, dict) or p.get("platform") not in ("naver", "blogspot"):
            raise invalid("publishing 항목에는 platform(naver|blogspot)이 필요합니다.")
        if not isinstance(p.get("publishing_id"), str) or not p["publishing_id"].strip():
            raise invalid("publishing 항목에는 publishing_id가 필요합니다.")
        if not p.get("human_published_at"):
            continue  # not yet published by a person; nothing to measure against
        at = _parse_time(p["human_published_at"], "human_published_at")
        current = published.get(p["platform"])
        if current is None or at > current["_at"]:
            published[p["platform"]] = {"platform": p["platform"], "publishing_id": p["publishing_id"],
                                        "human_published_at": p["human_published_at"], "_at": at}
    return published


def _parse_time(value, field="measured_at"):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise invalid(f"{field}은 ISO 8601 날짜·시각이어야 합니다.", {field: str(value)[:40]}) from None
    return parsed if parsed.tzinfo else parsed.astimezone()


def _link_publishing(rows, published, warnings):
    """Drop pre-publication measurements and add days since publication."""
    if published is None:
        warnings.append(warning("PUBLISHING_REFS_MISSING", "Publishing 참조가 없어 발행 시점 대비 분석을 하지 않았습니다."))
        return rows
    early = [r for r in rows if r["platform"] in published and r["_at"] < published[r["platform"]]["_at"]]
    if early:
        warnings.append(warning("MEASURED_BEFORE_PUBLISH", "발행 시각 이전 측정값은 제외했습니다.", count=len(early)))
    unlinked = sorted({r["platform"] for r in rows} - set(published))
    if unlinked:
        warnings.append(warning("METRICS_WITHOUT_PUBLISHING", "발행 기록이 없는 플랫폼의 측정값입니다.", platforms=unlinked))
    missing = sorted(set(published) - {r["platform"] for r in rows})
    if missing:
        warnings.append(warning("NO_METRICS_FOR_PLATFORM", "발행했지만 측정값이 없는 플랫폼이 있습니다.", platforms=missing))
    early_ids = {id(r) for r in early}
    kept = [r for r in rows if id(r) not in early_ids]
    if not kept:
        raise invalid("발행 이후 측정값이 없습니다.")
    return kept


def _add_days(summary, rows, published):
    if not published:
        return
    latest = {}
    for r in rows:
        key = (r["platform"], r["metric_name"])
        if key not in latest or r["_at"] > latest[key]:
            latest[key] = r["_at"]
    for s in summary:
        pub = published.get(s["platform"])
        if pub:
            s["publishing_id"] = pub["publishing_id"]
            s["days_since_publish"] = (latest[(s["platform"], s["metric_name"])] - pub["_at"]).days


def _aggregate(rows):
    series = defaultdict(list)
    for r in rows:
        series[(r["platform"], r["metric_name"])].append((r["_at"], r["measured_at"], float(r["metric_value"])))
    out = []
    for (platform, name), points in sorted(series.items()):
        points.sort(key=lambda p: p[0])
        values = [v for _, _, v in points]
        entry = {"platform": platform, "metric_name": name, "latest": values[-1], "latest_at": points[-1][1],
                 "mean": round(mean(values), 4), "max": max(values), "samples": len(values)}
        if len(values) >= 2:
            prev = values[-2]
            entry["change_vs_previous"] = values[-1] - prev
            entry["change_ratio"] = round((values[-1] - prev) / prev, 4) if prev else None
        out.append(entry)
    return out


def _rule_suggestions(summary):
    latest = {(s["platform"], s["metric_name"]): s["latest"] for s in summary}
    tips = []
    for platform in sorted({p for p, _ in latest}):
        views = latest.get((platform, "views"))
        reactions = [latest[(platform, k)] for k in ("likes", "comments") if (platform, k) in latest]
        if views and views > 0 and reactions:
            engage = sum(reactions) / views
            if engage < LOW_ENGAGEMENT:
                tips.append({"platform": platform, "type": "engagement", "basis": f"참여율 {engage:.2%}",
                             "suggestion": "도입부와 마무리에 독자 질문·행동 유도를 추가하는 방안을 검토하세요(가설)."})
        bounce = latest.get((platform, "bounce_rate"))
        if bounce is not None and bounce > 0.7:
            tips.append({"platform": platform, "type": "bounce", "basis": f"이탈률 {bounce:.0%}",
                         "suggestion": "첫 화면의 핵심 요약과 소제목 구성을 점검하세요(가설)."})
        read = latest.get((platform, "avg_read_seconds"))
        if read is not None and read < 30:
            tips.append({"platform": platform, "type": "read_time", "basis": f"평균 체류 {read:.0f}초",
                         "suggestion": "검색 의도와 제목·도입부가 일치하는지 확인하세요(가설)."})
    for s in summary:
        if s.get("days_since_publish") is not None and s["days_since_publish"] < EARLY_DAYS:
            continue  # the first-week drop after publication is expected
        if s["metric_name"] == "views" and s.get("change_ratio") is not None and s["change_ratio"] <= -0.3:
            tips.append({"platform": s["platform"], "type": "decline", "basis": f"조회수 {s['change_ratio']:.0%} 변동",
                         "suggestion": "시기성 주제인지, 검색 노출 순위 변화가 있었는지 확인하세요(가설)."})
    return tips


def analyze(inp, refs, llm):
    require_refs(refs, "content_id")
    rows = _parse(inp)
    published = _parse_publishing(inp)
    warnings = []
    rows = _link_publishing(rows, published, warnings)
    summary = _aggregate(rows)
    _add_days(summary, rows, published)
    unknown = sorted({r["metric_name"] for r in rows} - set(KNOWN_METRICS))
    if unknown:
        warnings.insert(0, warning("UNKNOWN_METRICS", "알 수 없는 지표는 집계만 하고 해석하지 않았습니다.", metrics=unknown))
    suggestions = _rule_suggestions(summary)
    if llm is not None:
        def validate(d):
            if not isinstance(d, dict) or not isinstance(d.get("suggestions"), list):
                raise ValueError("suggestions 배열이 필요합니다.")
            return d
        prompt = (f"집계 결과:\n{summary}\n규칙 기반 제안:\n{suggestions}\n\n"
                  '출력: {"suggestions":[{"platform":"","basis":"집계 수치 인용","suggestion":"가설 형태의 제안"}]}')
        for s in call_json(llm, role_for("performance_analysis", "lightweight"), SYSTEM, prompt, validate)["suggestions"]:
            if isinstance(s, dict) and str(s.get("suggestion", "")).strip() and str(s.get("basis", "")).strip():
                platform = s.get("platform") if s.get("platform") in ("naver", "blogspot") else None
                suggestions.append({"platform": platform, "type": "ai", "basis": str(s["basis"]).strip(),
                                    "suggestion": str(s["suggestion"]).strip()})
    publishing = [{k: v for k, v in p.items() if k != "_at"} for p in (published or {}).values()]
    return {"summary": summary, "suggestions": suggestions, "publishing": publishing, "warnings": warnings}


def run(request, *, llm=None):
    return execute(request, MODULE, lambda inp, refs: analyze(inp, refs, llm))
