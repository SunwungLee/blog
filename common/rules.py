"""Content rules shared by every skill that generates or rewrites article text (AGENTS.md)."""

import re

from common import privacy
from common.config import forbidden_phrases

BANNED_FINANCE = re.compile(
    r"매수\s*(?:추천|하세요|를 권)|수익\s*(?:보장|확정)|원금\s*보장|반드시\s*(?:오릅|상승)|확실한\s*수익|무조건\s*(?:이득|수익)"
)
FINANCE_NOTICE = "본 글은 정보 제공을 목적으로 하며 투자 권유나 금융상품 매수 추천이 아닙니다."
SPONSOR_NOTICE = "본 글에는 광고·협찬 또는 제휴 링크가 포함되어 있습니다."
INFO_DATE_LINE = re.compile(r"^>?\s*정보 기준일\s*:", re.M)


def content_problems(texts, ctype, blocked_terms=()):
    """Problems that any generated text must not have: finance promises, stock AI phrases, PII."""
    joined = "\n".join(t for t in texts if isinstance(t, str))
    out = []
    if ctype == "finance" and BANNED_FINANCE.search(joined):
        out.append("매수 추천·수익 보장 표현이 있습니다.")
    stock = [p for p in forbidden_phrases() if p in joined]
    if stock:
        out.append(f"AI 특유의 상투 표현을 쓰지 마세요: {stock}")
    kinds = privacy.scan_values(list(texts), blocked_terms)
    if kinds:
        out.append(f"식별 정보가 포함되었습니다: {kinds}")
    return out


def lost_notices(original, revised):
    """Required notices present in `original` that `revised` dropped (exact sentences)."""
    lost = [n for n in (FINANCE_NOTICE, SPONSOR_NOTICE) if n in original and n not in revised]
    if INFO_DATE_LINE.search(original) and not INFO_DATE_LINE.search(revised):
        lost.append("정보 기준일")
    return lost
