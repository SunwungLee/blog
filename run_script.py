"""Run one deterministic script with the standard envelope (Phase_0_design.md 4.3).

`python run_script.py <script-name> [--hash-only] < request.json > response.json`

`module` in the request is the script name. Supported inputs:
- data-validator:  {"message": {...}} or {"instance": ..., "schema": {...}}
- html-converter:  {"markdown": "...", "target": "html" | "naver"}
- seo-checker:     {"markdown", "title", "primary_keyword", "related_keywords"?, "meta_description"?, "config"?}
- image-processor: {"width", "height", "max_width"?} for a resize plan, or {"src", "dst", "max_width"?} to resize
- id-allocator:    {"kind": "topic" | "content", "date": "YYYY-MM-DD", "count"?, "floor"?} (workflow only)
"""

import argparse

from common.envelope import execute, failure, hash_only
from common.errors import SkillError
from common.loader import load_script
from common.util import invalid, require_str
from run_skill import emit, load_failure, read_request


def _data_validator(mod, inp):
    if "message" in inp:
        errors = mod.validate_envelope(inp["message"])
    elif isinstance(inp.get("schema"), dict) and "instance" in inp:
        errors = mod.validate(inp["instance"], inp["schema"])
    else:
        raise invalid("message 또는 instance+schema가 필요합니다.")
    return {"valid": not errors, "errors": errors}


def _html_converter(mod, inp):
    markdown = require_str(inp, "markdown")
    target = inp.get("target", "html")
    if target not in ("html", "naver"):
        raise invalid("target은 html 또는 naver여야 합니다.")
    return {"html": mod.markdown_to_naver(markdown) if target == "naver" else mod.markdown_to_html(markdown)}


def _seo_checker(mod, inp):
    related = inp.get("related_keywords", [])
    meta = inp.get("meta_description") or ""
    cfg = inp.get("config")
    if not isinstance(related, list) or any(not isinstance(k, str) for k in related) or not isinstance(meta, str) \
            or (cfg is not None and not isinstance(cfg, dict)):
        raise invalid("related_keywords·meta_description·config 형식이 올바르지 않습니다.")
    return mod.check(require_str(inp, "markdown"), require_str(inp, "title"), require_str(inp, "primary_keyword"), related, meta, cfg)


def _positive_int(inp, key, default=None):
    value = inp.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise invalid(f"{key}는 양의 정수여야 합니다.")
    return value


def _image_processor(mod, inp):
    max_width = _positive_int(inp, "max_width", 1200)
    if "src" in inp or "dst" in inp:
        return mod.resize_image(require_str(inp, "src"), require_str(inp, "dst"), max_width)
    width, height = mod.plan_resize(_positive_int(inp, "width"), _positive_int(inp, "height"), max_width)
    return {"width": width, "height": height}


def _id_allocator(mod, inp):
    ids = mod.allocate(inp.get("kind"), inp.get("date"), inp.get("count", 1), inp.get("floor", 0))
    return {"ids": ids}


HANDLERS = {
    "data-validator": _data_validator,
    "html-converter": _html_converter,
    "seo-checker": _seo_checker,
    "image-processor": _image_processor,
    "id-allocator": _id_allocator,
}


def run(name, request, hash_mode=False):
    handler = HANDLERS.get(name)
    if handler is None:
        return failure(request, {}, SkillError("INVALID_INPUT", "알 수 없는 script입니다."))
    if hash_mode:
        return hash_only(request, name)
    try:
        module = load_script(name)
    except Exception:  # noqa: BLE001 - a broken module must still answer with an envelope
        return load_failure(request)
    return execute(request, name, lambda inp, refs: handler(module, inp))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("script")
    parser.add_argument("--hash-only", action="store_true", help="return input_hash without running the script")
    args = parser.parse_args(argv)
    request, error = read_request()
    if error:
        return emit(error)
    return emit(run(args.script, request, args.hash_only))


if __name__ == "__main__":
    raise SystemExit(main())
