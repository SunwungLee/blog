"""Checks that a rewrite changed wording only, never facts, links or required notices."""

import re

from common import rules

_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
_URL = re.compile(r"https?://[^\s)>\]\"'<]+")
_LIST_MARKER = re.compile(r"^\s*\d+[.)]\s+", re.M)
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
NOTICE_MARKERS = ("투자 권유", "광고", "협찬", "정보 기준일")


def numbers(text):
    return {n.replace(",", "") for n in _NUM.findall(_LIST_MARKER.sub("", text))}


def urls(text):
    return {u.rstrip(".,;:!?") for u in _URL.findall(text)}


def facts_changed(original, revised):
    """Return human-readable problems; empty list means facts are preserved."""
    problems = []
    added = numbers(revised) - numbers(original)
    if added:
        problems.append(f"원문에 없는 숫자가 추가되었습니다: {sorted(added)[:5]}")
    lost = numbers(original) - numbers(revised)
    if lost:
        problems.append(f"원문의 숫자가 빠졌습니다: {sorted(lost)[:5]}")
    lost_urls = urls(original) - urls(revised)
    if lost_urls:
        problems.append(f"링크가 삭제되었습니다: {sorted(lost_urls)[:3]}")
    new_urls = urls(revised) - urls(original)
    if new_urls:
        problems.append(f"원문에 없는 링크가 추가되었습니다: {sorted(new_urls)[:3]}")
    if len(_IMAGE.findall(revised)) > len(_IMAGE.findall(original)):
        problems.append("원문에 없는 이미지가 추가되었습니다(이미지는 {{image:ID}}로만 배치).")
    lost_notices = [m for m in NOTICE_MARKERS if m in original and m not in revised]
    lost_notices += [n for n in rules.lost_notices(original, revised) if n not in lost_notices]
    if lost_notices:
        problems.append(f"고지 문구가 삭제되었습니다: {lost_notices}")
    return problems


def text_overlap(a, b, n=4):
    """Character n-gram Jaccard similarity in [0, 1]."""
    def grams(t):
        t = re.sub(r"\s+", "", re.sub(r"<[^>]+>|[#*>`\-]", "", t))
        return {t[i:i + n] for i in range(max(len(t) - n + 1, 0))}

    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)
