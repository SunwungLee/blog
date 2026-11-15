"""Search-result normalization and official-source detection."""

from urllib.parse import urlparse

OFFICIAL_SUFFIXES = (".go.kr", ".gov", ".gov.kr", ".mil.kr", ".sc.kr")
OFFICIAL_DOMAINS = (
    "fss.or.kr", "bok.or.kr", "krx.co.kr", "kofia.or.kr", "kdic.or.kr",
    "nps.or.kr", "kosis.kr", "law.go.kr", "gov.kr", "kasb.or.kr",
)


def hostname(url):
    try:
        parsed = urlparse(url)
    except ValueError:
        return ""
    if parsed.scheme not in ("http", "https"):
        return ""
    return (parsed.hostname or "").lower()


def is_valid_url(url):
    return isinstance(url, str) and bool(hostname(url.strip()))


def is_official(url):
    host = hostname(url)
    if not host:
        return False
    if host.endswith(OFFICIAL_SUFFIXES):
        return True
    return any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS)


def normalize_results(raw):
    """Keep usable results only: valid http(s) URL, de-duplicated, with a title."""
    if not isinstance(raw, list):
        return []
    seen, results = set(), []
    for item in raw:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip()
        if not is_valid_url(url) or not title:
            continue
        key = url.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "title": title,
            "url": url,
            "publisher": str(item.get("publisher") or hostname(url)).strip(),
            "snippet": str(item.get("snippet", "")).strip()[:600],
            "published_at": item.get("published_at") if isinstance(item.get("published_at"), str) and item.get("published_at") else None,
        })
    return results


def run_search(search, query, max_results=8):
    """Call the injected search provider; raise a structured error if absent or failing."""
    from common import usage
    from common.errors import SkillError, call_provider

    if search is None:
        raise SkillError("AUTH_OR_PERMISSION", "검색 공급자가 설정되지 않았습니다.")
    usage.search_call()
    return normalize_results(call_provider(search, query, max_results, provider="검색"))[:max_results]
