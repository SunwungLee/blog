"""seo-optimization: mechanical SEO check first, AI rewrite only when needed, facts frozen."""

import re

from common import ids, rules
from common.config import quality, role_for
from common.facts import facts_changed, numbers
from common.envelope import execute, require_refs
from common.llm import call_json, run_with_quality
from common.loader import load_script
from common.util import invalid, require_content_type, require_str, warning

MODULE = "seo-optimization"
HEAD_CHECKS = {"title_length", "keyword_in_title", "meta_length"}

SYSTEM = (
    "당신은 SEO 편집자입니다. 사실·수치·링크·고지 문구는 절대 바꾸지 않고 제목, 소제목, 도입부, 문장 표현, 메타 설명만 다듬어 JSON만 출력합니다. "
    "키워드를 억지로 반복하지 마세요."
)


def _parse(inp):
    article = require_str(inp, "article_markdown")
    title = require_str(inp, "title")
    primary = require_str(inp, "primary_keyword")
    related = inp.get("related_keywords", [])
    if not isinstance(related, list) or any(not isinstance(k, str) for k in related):
        raise invalid("related_keywords는 문자열 목록이어야 합니다.")
    version = inp.get("version_no", 1)
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise invalid("version_no는 1 이상의 정수여야 합니다.")
    meta = inp.get("meta_description") or ""
    intent = inp.get("search_intent") or ""
    cfg = inp.get("seo_config")
    if not isinstance(meta, str) or not isinstance(intent, str) or (cfg is not None and not isinstance(cfg, dict)):
        raise invalid("meta_description·search_intent는 문자열, seo_config는 객체여야 합니다.")
    ctype = inp.get("content_type")
    if ctype is not None:
        require_content_type(ctype)
    blocked = inp.get("blocked_terms") or []
    if not isinstance(blocked, list):
        raise invalid("blocked_terms는 문자열 목록이어야 합니다.")
    return article, title, primary, related, intent, meta, version, cfg, ctype, blocked


def _validate(data):
    if not isinstance(data, dict):
        raise ValueError("객체여야 합니다.")
    for key in ("title", "meta_description", "body_markdown"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"{key}가 필요합니다.")
    if not isinstance(data.get("changes", []), list):
        data["changes"] = []
    return data


def _validate_head(data):
    if not isinstance(data, dict):
        raise ValueError("객체여야 합니다.")
    for key in ("title", "meta_description"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"{key}가 필요합니다.")
    if not isinstance(data.get("changes", []), list):
        data["changes"] = []
    return data


def _chars(text):
    return len(re.sub(r"\s", "", text))


def _problems(article, data, ctype, blocked):
    problems = facts_changed(article, data["body_markdown"])
    added = numbers(f"{data['title']} {data['meta_description']}") - numbers(article)
    if added:
        problems.append(f"제목·메타 설명에 원문에 없는 숫자가 있습니다: {sorted(added)[:5]}")
    growth = quality("seo_max_body_growth", 0.1)
    if _chars(data["body_markdown"]) > _chars(article) * (1 + growth):
        problems.append(f"본문 분량을 {growth:.0%} 넘게 늘리지 마세요(사실 검증되지 않은 문장 추가 금지).")
    problems += rules.content_problems([data["title"], data["meta_description"], data["body_markdown"]], ctype, blocked)
    return problems


def optimize(inp, refs, llm):
    require_refs(refs, "content_id")
    article, title, primary, related, intent, meta, version, cfg, ctype, blocked = _parse(inp)
    checker = load_script("seo-checker")
    before = checker.check(article, title, primary, related, meta, cfg)
    if before["passed"] and meta:
        return {"optimized": False, "requires_refactcheck": False, "title": title, "meta_description": meta, "changes": [],
                "before": before, "after": before, "warnings": [], "artifact": _artifact(refs, version, article)}

    failed = {c["name"] for c in before["checks"] if not c["passed"] and c["severity"] == "error"}
    head_only = failed <= HEAD_CHECKS

    def produce(problems):
        if head_only:
            prompt = (
                f"대표 키워드: {primary}\n연관 키워드: {related}\n검색 의도: {intent}\n현재 제목: {title}\n"
                f"현재 메타 설명: {meta or '없음'}\n실패한 SEO 검사: {[c['message'] for c in before['checks'] if not c['passed']]}\n"
                + (f"이전 결과의 문제(반드시 고칠 것): {problems}\n" if problems else "")
                + f"\n원고 앞부분:\n{article[:800]}\n\n"
                '출력: {"title":"","meta_description":"","changes":["변경 요약"]}'
            )
            data = call_json(llm, role_for("seo_review", "lightweight"), SYSTEM, prompt, _validate_head)
            data["body_markdown"] = article
            return data
        prompt = (
            f"대표 키워드: {primary}\n연관 키워드: {related}\n검색 의도: {intent}\n현재 제목: {title}\n"
            f"실패한 SEO 검사: {[c['message'] for c in before['checks'] if not c['passed']]}\n"
            "본문 분량 부족은 고치지 말고 그대로 두세요. 새 사실·문단을 추가하지 마세요.\n"
            + (f"이전 결과의 문제(반드시 고칠 것): {problems}\n" if problems else "")
            + f"\n원고:\n{article}\n\n"
            '출력: {"title":"","meta_description":"","body_markdown":"","changes":["변경 요약"]}'
        )
        return call_json(llm, role_for("seo_review", "lightweight"), SYSTEM, prompt, _validate)

    data = run_with_quality(produce, lambda d: _problems(article, d, ctype, blocked))
    body = data["body_markdown"].rstrip() + "\n"
    after = checker.check(body, data["title"], primary, related, data["meta_description"], cfg)
    warnings = []
    if not after["passed"]:
        warnings.append(warning("SEO_NOT_FULLY_PASSED", "일부 SEO 필수 검사를 통과하지 못했습니다.",
                                failed=[c["name"] for c in after["checks"] if not c["passed"] and c["severity"] == "error"]))
    changed = body.strip() != article.strip()
    if changed:
        warnings.append(warning("REFACTCHECK_REQUIRED", "본문 문장이 바뀌었으므로 승인 전 사실 검증을 다시 실행해야 합니다."))
    return {
        "optimized": True, "requires_refactcheck": changed, "title": data["title"].strip(),
        "meta_description": data["meta_description"].strip(),
        "changes": [c for c in data.get("changes", []) if isinstance(c, str)], "before": before, "after": after,
        "warnings": warnings, "artifact": _artifact(refs, version, body),
    }


def _artifact(refs, version, content):
    return {"file_name": ids.file_name(refs["content_id"], "final", version, "md"),
            "drive_path": ids.drive_path(refs["content_id"], "final"), "content_type": "text/markdown", "content": content}


def run(request, *, llm=None):
    return execute(request, MODULE, lambda inp, refs: optimize(inp, refs, llm))
