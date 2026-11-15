"""image-preparation: image plan, rights metadata and resize plans (no image is used without confirmed rights)."""

import re

from common import ids, privacy
from common.config import role_for
from common.envelope import execute, require_refs
from common.llm import call_json
from common.loader import load_script
from common.util import invalid, now_iso, require_str, warning

MODULE = "image-preparation"
SOURCE_TYPES = ("own", "licensed", "ai_generated")
DEFAULT_MAX_IMAGES = 6
_FACE = re.compile(r"얼굴|정면 사진|실명|이름표|간판|번지|아파트 동")

SYSTEM = (
    "당신은 블로그 이미지 기획자입니다. 글의 흐름에 필요한 이미지 위치와 용도를 JSON으로 출력합니다. "
    "사람 얼굴, 실명, 위치를 알 수 있는 요소는 계획에 넣지 마세요. 직접 촬영(own) 이미지는 촬영 가이드를, "
    "AI 생성(ai_generated)은 일반적인 장면 설명 프롬프트를 쓰세요."
)


def _parse(inp):
    article = require_str(inp, "article_markdown")
    constraints = inp.get("constraints") or {}
    if not isinstance(constraints, dict):
        raise invalid("constraints는 객체여야 합니다.")
    max_images = constraints.get("max_images", DEFAULT_MAX_IMAGES)
    allowed = constraints.get("allowed_source_types", list(SOURCE_TYPES))
    max_width = constraints.get("max_width", 1200)
    if isinstance(max_images, bool) or not isinstance(max_images, int) or not 1 <= max_images <= 15:
        raise invalid("max_images는 1~15 정수여야 합니다.")
    if isinstance(max_width, bool) or not isinstance(max_width, int) or not 1 <= max_width <= 4000:
        raise invalid("max_width는 1~4000 정수여야 합니다.")
    if not isinstance(allowed, list) or not allowed or any(a not in SOURCE_TYPES for a in allowed):
        raise invalid("allowed_source_types가 올바르지 않습니다.")
    assets = inp.get("assets", [])
    if not isinstance(assets, list):
        raise invalid("assets는 목록이어야 합니다.")
    blocked = inp.get("blocked_terms") or []
    if not isinstance(blocked, list):
        raise invalid("blocked_terms는 문자열 목록이어야 합니다.")
    return article, max_images, allowed, assets, blocked, max_width


def _prompt(article, max_images, allowed):
    headings = [m.group(1) for m in re.finditer(r"^#{2,3}\s+(.+)$", article, re.M)]
    return (
        f"최대 {max_images}개, 허용 출처 유형: {allowed}\n소제목: {headings}\n\n원고 앞부분:\n{article[:1500]}\n\n"
        '출력: {"images":[{"slot_heading":"소제목","purpose":"","alt_text":"","caption":"",'
        '"source_type":"own|licensed|ai_generated","guide":"촬영 가이드 또는 생성 프롬프트"}]}'
    )


def _validate(data):
    if not isinstance(data, dict) or not isinstance(data.get("images"), list) or not data["images"]:
        raise ValueError("images 배열이 필요합니다.")
    return data


def _record_asset(asset, allowed, max_width, resizer, stamp):
    problems = []
    stype = asset.get("source_type")
    if stype not in allowed:
        problems.append("허용되지 않은 출처 유형")
    image_id = asset.get("image_id") if isinstance(asset.get("image_id"), str) and asset["image_id"].strip() else None
    if image_id is None:
        problems.append("image_id 없음(Images 시트에서 발급된 ID 필요)")
    if not asset.get("drive_file_id"):
        problems.append("drive_file_id 없음")
    if not str(asset.get("rights_note", "")).strip() or not asset.get("rights_checked_at"):
        problems.append("사용 권한 확인 기록 없음")
    rec = {
        "image_id": image_id, "source_type": stype,
        "drive_file_id": asset.get("drive_file_id"), "rights_note": str(asset.get("rights_note", "")).strip(),
        "rights_checked_at": asset.get("rights_checked_at"), "status": "RIGHTS_CONFIRMED" if not problems else "PENDING_RIGHTS",
        "problems": problems,
    }
    w, h = asset.get("width"), asset.get("height")
    if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
        rec["resize_to"] = dict(zip(("width", "height"), resizer.plan_resize(w, h, max_width)))
    return rec


def prepare(inp, refs, llm, now):
    require_refs(refs, "content_id")
    article, max_images, allowed, assets, blocked, max_width = _parse(inp)
    resizer = load_script("image-processor")
    stamp = now_iso(now)
    data = call_json(llm, role_for("image_planning", "lightweight"), SYSTEM, _prompt(article, max_images, allowed), _validate)
    plan, warnings = [], []
    for raw in data["images"]:
        if not isinstance(raw, dict) or raw.get("source_type") not in allowed:
            warnings.append(warning("IMAGE_DROPPED", "허용되지 않은 유형이어서 제외했습니다."))
            continue
        texts = {k: str(raw.get(k, "")).strip() for k in ("slot_heading", "purpose", "alt_text", "caption", "guide")}
        if not texts["alt_text"] or not texts["purpose"]:
            warnings.append(warning("IMAGE_DROPPED", "alt_text/purpose가 없어 제외했습니다."))
            continue
        if privacy.scan_values(list(texts.values()), blocked) or _FACE.search(" ".join(texts.values())):
            warnings.append(warning("IMAGE_DROPPED_PRIVACY", "식별 정보 가능성이 있어 제외했습니다.", slot=texts["slot_heading"]))
            continue
        plan.append({"image_id": ids.new_uuid(), "source_type": raw["source_type"], "status": "PLANNED", **texts})
        if len(plan) == max_images:
            break
    records = [_record_asset(a, allowed, max_width, resizer, stamp) for a in assets if isinstance(a, dict)]
    blocked_records = [r for r in records if r["status"] != "RIGHTS_CONFIRMED"]
    pending = [r["image_id"] for r in blocked_records if r["image_id"]]
    if blocked_records:
        warnings.append(warning("RIGHTS_UNCONFIRMED", "권한이 확인되지 않은 이미지는 발행물에 사용할 수 없습니다.", image_ids=pending,
                                drive_file_ids=[r["drive_file_id"] for r in blocked_records if not r["image_id"] and r["drive_file_id"]]))
    return {
        "image_plan": plan, "assets": records,
        "usable_image_ids": [r["image_id"] for r in records if r["status"] == "RIGHTS_CONFIRMED"],
        "unusable_image_ids": pending, "warnings": warnings, "prepared_at": stamp,
    }


def run(request, *, llm=None, now=None):
    return execute(request, MODULE, lambda inp, refs: prepare(inp, refs, llm, now))
