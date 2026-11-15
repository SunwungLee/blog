"""Detection of identifying information that must not reach prompts or search."""

import re

_PROVINCES = (
    r"(?:서울|부산|대구|인천|광주|대전|울산|세종)(?:특별시|광역시|특별자치시)?"
    r"|(?:경기|강원|충청[남북]|전라[남북]|경상[남북]|충[남북]|전[남북]|경[남북]|제주)(?:특별자치)?도"
)
_PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    # Hangul counts as a word character, so `\b` would miss "010-1234-5678입니다".
    "phone": re.compile(r"(?<!\d)0\d{1,2}[-. ]?\d{3,4}[-. ]?\d{4}(?!\d)"),
    "resident_number": re.compile(r"(?<!\d)\d{6}[-. ]?[1-4]\d{6}(?!\d)"),
    "address": re.compile(
        rf"(?:{_PROVINCES})\s*[가-힣]{{1,10}}(?:시|군|구)(?![가-힣])"
        r"|(?<![가-힣])[가-힣]{1,10}(?:시|군|구)\s+[가-힣0-9]{1,15}(?:로|길)\s?\d+(?:-\d+)?(?![\d가-힣])"
        r"|(?<!\d)\d{1,4}동\s*\d{1,4}호"
    ),
}


def _terms(blocked_terms):
    return [t for t in blocked_terms or () if isinstance(t, str) and t.strip()]


def find_pii(text, blocked_terms=()):
    """Return the kinds of identifying data found in `text`."""
    if not isinstance(text, str):
        return []
    found = [kind for kind, pattern in _PATTERNS.items() if pattern.search(text)]
    lowered = text.lower()
    if any(t.strip().lower() in lowered for t in _terms(blocked_terms)):
        found.append("blocked_term")
    return found


def scan_values(value, blocked_terms=()):
    """Scan every string inside a JSON-like value; return sorted unique kinds."""
    kinds = set()
    if isinstance(value, str):
        kinds.update(find_pii(value, blocked_terms))
    elif isinstance(value, dict):
        for item in value.values():
            kinds.update(scan_values(item, blocked_terms))
    elif isinstance(value, (list, tuple)):
        for item in value:
            kinds.update(scan_values(item, blocked_terms))
    return sorted(kinds)


def redact(text, blocked_terms=(), placeholder="[개인정보 생략]"):
    """Return `(masked_text, kinds)` so identifying data never reaches a prompt."""
    if not isinstance(text, str):
        return text, []
    kinds = find_pii(text, blocked_terms)
    if not kinds:
        return text, []
    for pattern in _PATTERNS.values():
        text = pattern.sub(placeholder, text)
    for term in sorted((t.strip() for t in _terms(blocked_terms)), key=len, reverse=True):
        text = re.sub(re.escape(term), placeholder, text, flags=re.I)
    return text, kinds
