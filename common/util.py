"""Small shared helpers: time, text normalization, input checks."""

import re
from datetime import datetime
from difflib import SequenceMatcher

from common.errors import SkillError

CONTENT_TYPES = ("experience", "finance", "review", "guide", "compare")
TYPE_LABELS = {
    "experience": "육아·생활 경험담",
    "finance": "재테크·금융 정보",
    "review": "제품·서비스 리뷰",
    "guide": "정보·가이드",
    "compare": "비교·분석",
}
FIRST_PERSON = re.compile(r"(?<![가-힣])(제가|내가|저는|저희|우리 (?:아이|애|가족)가? 직접|직접 (?:겪|해 ?봤|써 ?봤|사용해 ?봤))")


def now_iso(now=None):
    value = now() if callable(now) else now
    if value is None:
        value = datetime.now().astimezone()
    if value.tzinfo is None:
        value = value.astimezone()
    return value.isoformat(timespec="seconds")


def invalid(message, details=None):
    return SkillError("INVALID_INPUT", message, details=details)


def require_str(inp, key):
    value = inp.get(key)
    if not isinstance(value, str) or not value.strip():
        raise invalid(f"{key}는 비어 있지 않은 문자열이어야 합니다.")
    return value.strip()


def require_content_type(value, allowed=CONTENT_TYPES):
    if value not in allowed:
        raise invalid("지원하지 않는 content_type입니다.", {"content_type": value})
    return value


def normalize_text(text):
    return re.sub(r"[\s\W_]+", "", str(text).lower())


def similar(a, b, threshold=0.8):
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if na in nb or nb in na:
        return min(len(na), len(nb)) >= 6
    return SequenceMatcher(None, na, nb).ratio() >= threshold


def warning(code, message, **extra):
    item = {"code": code, "message": message}
    item.update(extra)
    return item
