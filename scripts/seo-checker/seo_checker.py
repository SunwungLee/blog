"""Mechanical SEO checks for Korean markdown articles (no AI)."""

import re

from common.config import quality

DEFAULTS = {
    "min_chars": quality("min_body_chars", 1500),
    "title_min": 15,
    "title_max": 45,
    "meta_min": 70,
    "meta_max": 160,
    "density_min": 0.3,
    "density_max": 3.0,
    "max_paragraph_chars": 600,
}

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)
_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
_LINK = re.compile(r"(?<!!)\[[^\]]+\]\((https?://[^)\s]+)\)")


def _plain(markdown):
    text = _IMAGE.sub("", markdown)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    return re.sub(r"[*_`>|-]", "", text)


def _check(name, ok, message, severity="error", value=None):
    return {"name": name, "passed": bool(ok), "severity": severity, "message": message, "value": value}


def check(markdown, title, primary_keyword, related_keywords=(), meta_description="", config=None):
    cfg = {**DEFAULTS, **(config or {})}
    plain = _plain(markdown)
    chars = len(re.sub(r"\s", "", plain))
    headings = [(len(m.group(1)), m.group(2)) for m in _HEADING.finditer(markdown)]
    body_headings = [h for h in headings if h[0] >= 2]
    kw = primary_keyword.strip()
    occurrences = plain.count(kw) if kw else 0
    density = (occurrences * len(re.sub(r"\s", "", kw)) / chars * 100) if chars and kw else 0.0
    first_200 = re.sub(r"\s", "", plain)[:200]
    levels = [lvl for lvl, _ in headings]
    skipped = any(b - a > 1 for a, b in zip(levels, levels[1:]))
    paragraphs = [p for p in re.split(r"\n\s*\n", markdown) if p.strip() and not p.lstrip().startswith(("#", "|", "-", "*", "!", ">"))]
    long_paragraphs = [p for p in paragraphs if len(p) > cfg["max_paragraph_chars"]]
    missing_alt = [m for m in _IMAGE.findall(markdown) if not m.strip()]
    external = _LINK.findall(markdown)

    checks = [
        _check("title_length", cfg["title_min"] <= len(title.strip()) <= cfg["title_max"],
               f"제목 길이는 {cfg['title_min']}~{cfg['title_max']}자 권장", value=len(title.strip())),
        _check("keyword_in_title", bool(kw) and kw in title, "제목에 대표 키워드 포함"),
        _check("keyword_in_intro", bool(kw) and kw.replace(" ", "") in first_200, "도입부(200자)에 대표 키워드 포함"),
        _check("keyword_in_heading", any(kw in h for _, h in body_headings), "소제목에 대표 키워드 포함", severity="warning"),
        _check("keyword_density", cfg["density_min"] <= density <= cfg["density_max"],
               f"키워드 밀도 {cfg['density_min']}~{cfg['density_max']}% 권장", value=round(density, 2)),
        _check("min_length", chars >= cfg["min_chars"], f"본문 {cfg['min_chars']}자 이상", value=chars),
        _check("single_h1", levels.count(1) <= 1, "H1은 최대 1개"),
        _check("heading_hierarchy", not skipped, "소제목 단계를 건너뛰지 않음", severity="warning"),
        _check("has_subheadings", len(body_headings) >= 2, "소제목 2개 이상"),
        _check("paragraph_length", not long_paragraphs, "문단이 너무 길지 않음", severity="warning", value=len(long_paragraphs)),
        _check("image_alt_text", not missing_alt, "모든 이미지에 대체 텍스트 있음"),
        _check("related_keywords_used",
               sum(1 for k in related_keywords if k and k in plain) >= min(2, len(list(related_keywords))),
               "연관 키워드를 본문에 사용", severity="warning"),
    ]
    if meta_description:
        checks.append(_check("meta_length", cfg["meta_min"] <= len(meta_description) <= cfg["meta_max"],
                             f"메타 설명 {cfg['meta_min']}~{cfg['meta_max']}자", value=len(meta_description)))
    checks.append(_check("has_source_links", bool(external), "출처 링크 포함", severity="warning", value=len(external)))
    failed = [c for c in checks if not c["passed"]]
    return {
        "passed": not any(c["severity"] == "error" for c in failed),
        "error_count": sum(1 for c in failed if c["severity"] == "error"),
        "warning_count": sum(1 for c in failed if c["severity"] == "warning"),
        "checks": checks,
    }
