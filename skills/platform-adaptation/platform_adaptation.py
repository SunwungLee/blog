"""platform-adaptation: rewrite an approved article for one platform without changing facts."""

import re

from common import ids, rules
from common.config import quality, role_for, style_prompt
from common.envelope import execute, require_refs
from common.facts import facts_changed, text_overlap
from common.llm import call_json, run_with_quality
from common.loader import load_script
from common.util import invalid, require_content_type, require_str, warning

MODULE = "platform-adaptation"
PLATFORMS = ("naver", "blogspot")
# Blogspot keeps the SEO article's H2/H3 structure, so it is converted by script first;
# Naver needs a tone/paragraph rewrite and always uses AI (Phase 0 20.13).
SCRIPT_FIRST = ("blogspot",)
MAX_OVERLAP = quality("max_platform_overlap", 0.6)
_PLACEHOLDER = re.compile(r"\{\{image:([\w-]+)\}\}")
_RAW_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")

STYLE = {
    "naver": "네이버 블로그: 짧은 문단, 친근한 말투, 소제목은 간결하게, 이모지는 최소한으로, 문단 사이 여백을 넉넉하게. H1은 쓰지 마세요.",
    "blogspot": "Google Blogspot: 검색 노출을 고려한 정돈된 H2/H3 구조, 도입부에 핵심 요약, 표/목록 활용, 격식 있는 문체.",
}
SYSTEM = (
    "당신은 플랫폼 편집자입니다. 승인된 원고의 표현·구성·형식만 플랫폼에 맞게 바꾸고 사실, 수치, 링크, "
    "투자·광고 고지 문구는 그대로 유지합니다. JSON만 출력합니다. 다른 플랫폼과 같은 문장을 그대로 쓰지 마세요."
)


def _parse(inp):
    article = require_str(inp, "article_markdown")
    title = require_str(inp, "title")
    platform = inp.get("platform")
    if platform not in PLATFORMS:
        raise invalid("platform은 naver 또는 blogspot이어야 합니다.")
    ctype = require_content_type(inp.get("content_type"))
    version = inp.get("output_version_no", 1)
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise invalid("output_version_no는 1 이상의 정수여야 합니다.")
    targets = inp.get("target_platforms") or [platform]
    if not isinstance(targets, list) or platform not in targets or any(t not in PLATFORMS for t in targets):
        raise invalid("target_platforms는 현재 platform을 포함한 naver/blogspot 목록이어야 합니다.")
    other = inp.get("other_platform_output") or ""
    if not isinstance(other, str):
        raise invalid("other_platform_output은 문자열이어야 합니다.")
    raw_images = inp.get("images", [])
    if not isinstance(raw_images, list):
        raise invalid("images는 목록이어야 합니다.")
    images = {i["image_id"]: i for i in raw_images if isinstance(i, dict) and isinstance(i.get("image_id"), str) and i["image_id"]}
    blocked = inp.get("blocked_terms") or []
    if not isinstance(blocked, list):
        raise invalid("blocked_terms는 문자열 목록이어야 합니다.")
    return article, title, platform, version, other, images, ctype, set(targets), blocked


def _validate(data):
    if not isinstance(data, dict):
        raise ValueError("객체여야 합니다.")
    for key in ("title", "body_markdown"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"{key}가 필요합니다.")
    return data


def _apply_images(body, images, warnings):
    def strip_raw(m):
        warnings.append(warning("IMAGE_OMITTED", "{{image:ID}} 형식이 아닌 이미지는 권한 확인이 안 되어 제외했습니다."))
        return ""

    def repl(m):
        img = images.get(m.group(1))
        if img and img.get("status") == "RIGHTS_CONFIRMED" and img.get("url"):
            return f"![{img.get('alt_text', '')}]({img['url']})"
        warnings.append(warning("IMAGE_OMITTED", "권한 미확인 또는 URL 없는 이미지를 제외했습니다.", image_id=m.group(1)))
        return ""
    body = _RAW_IMAGE.sub(strip_raw, body)
    return _PLACEHOLDER.sub(repl, body)


def _place_images(body, images, warnings):
    """Script path: put each image after its `slot_heading` unless already placed."""
    for image_id, img in images.items():
        if f"{{{{image:{image_id}}}}}" in body:
            continue
        heading = str(img.get("slot_heading") or "").strip()
        pattern = re.compile(rf"^(#{{2,3}}\s+{re.escape(heading)}\s*)$", re.M) if heading else None
        if pattern and pattern.search(body):
            body = pattern.sub(lambda m: f"{m.group(1)}\n\n{{{{image:{image_id}}}}}", body, count=1)
        else:
            warnings.append(warning("IMAGE_NOT_PLACED", "배치할 소제목을 찾지 못해 이미지를 넣지 않았습니다.", image_id=image_id))
    return body


def _script_version(article, title, meta, other, ctype, blocked, max_overlap):
    """Return the script-converted article, or None when AI rewriting is needed."""
    body = re.sub(r"\A\s*#\s+[^\n]*\n+", "", article)  # the post title is set separately
    if other and text_overlap(body, other) > max_overlap:
        return None
    if rules.content_problems([title, meta, body], ctype, blocked):
        return None
    return {"title": title, "body_markdown": body, "meta_description": meta,
            "summary": "원고를 스크립트로 HTML 변환(AI 미사용)"}


def adapt(inp, refs, llm):
    require_refs(refs, "content_id")
    article, title, platform, version, other, images, ctype, targets, blocked = _parse(inp)
    mode = inp.get("adaptation_mode", "auto")
    if mode not in ("auto", "ai"):
        raise invalid("adaptation_mode는 auto 또는 ai여야 합니다.")
    meta = inp.get("meta_description") or ""
    if not isinstance(meta, str):
        raise invalid("meta_description은 문자열이어야 합니다.")
    converter = load_script("html-converter")
    max_overlap = quality("max_platform_overlap", 0.6)
    max_master_overlap = quality("max_master_overlap", 0.85)
    first_of_two = len(targets) == 2 and not other

    def produce(problems):
        prompt = (
            f"플랫폼 규칙: {STYLE[platform]}\n원본 제목: {title}\n{style_prompt()}\n"
            f"사용 가능한 이미지 ID(본문에 {{{{image:ID}}}} 형태로만 배치): {list(images)}\n"
            + (f"이전 결과의 문제(반드시 고칠 것): {problems}\n" if problems else "")
            + f"\n원고:\n{article}\n\n"
            '출력: {"title":"","body_markdown":"","meta_description":"","summary":"변경 요약"}'
        )
        return call_json(llm, role_for("platform_adaptation", "lightweight"), SYSTEM, prompt, _validate)

    def check(data):
        body = _PLACEHOLDER.sub("", data["body_markdown"])
        problems = facts_changed(article, body)
        if other and text_overlap(body, other) > max_overlap:
            problems.append("다른 플랫폼 결과물과 문장이 너무 비슷합니다(중복 문서 방지).")
        if first_of_two and text_overlap(body, article) > max_master_overlap:
            problems.append("두 플랫폼에 모두 발행하므로 원고 문장을 그대로 쓰지 말고 플랫폼에 맞게 다시 쓰세요.")
        problems += rules.content_problems([data["title"], str(data.get("meta_description") or ""), body], ctype, blocked)
        return problems

    data = None
    if mode == "auto" and platform in SCRIPT_FIRST:
        data = _script_version(article, title, meta.strip(), other, ctype, blocked, max_overlap)
    method = "script" if data else "ai"
    if data is None:
        data = run_with_quality(produce, check)
    warnings = []
    if first_of_two:
        warnings.append(warning("DUPLICATE_CHECK_PENDING", "다른 플랫폼 결과물이 아직 없어 원고 대비 중복만 확인했습니다. 다음 플랫폼 생성 시 이 결과를 other_platform_output으로 넘기세요."))
    body = data["body_markdown"]
    if method == "script":
        body = _place_images(body, images, warnings)
    body = _apply_images(body, images, warnings)
    html_body = converter.markdown_to_naver(body) if platform == "naver" else converter.markdown_to_html(body)
    return {
        "platform": platform, "adaptation_method": method, "title": data["title"].strip(),
        "meta_description": str(data.get("meta_description", "")).strip(),
        "adaptation_summary": str(data.get("summary", "")).strip(), "warnings": warnings,
        "artifact": {
            "file_name": ids.file_name(refs["content_id"], platform, version, "html"),
            "drive_path": ids.drive_path(refs["content_id"], platform),
            "content_type": "text/html", "content": html_body + "\n",
        },
        "markdown": body,
    }


def run(request, *, llm=None):
    return execute(request, MODULE, lambda inp, refs: adapt(inp, refs, llm))
