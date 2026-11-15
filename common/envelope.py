"""Versioned JSON request/response envelope shared by every skill."""

from common import ids, usage
from common.config import config_version
from common.errors import SkillError

SCHEMA_VERSION = "1.0"
REF_KEYS = ("discovery_run_id", "topic_id", "content_id", "drive_file_ids")


def _invalid(message, details=None):
    return SkillError("INVALID_INPUT", message, details=details)


def validate_request(request, module):
    if not isinstance(request, dict):
        raise _invalid("요청은 JSON 객체여야 합니다.")
    if request.get("schema_version") != SCHEMA_VERSION:
        raise _invalid(f"schema_version은 {SCHEMA_VERSION}이어야 합니다.")
    if not isinstance(request.get("run_id"), str) or not request["run_id"].strip():
        raise _invalid("run_id가 필요합니다.")
    if request.get("module") != module:
        raise _invalid(f"module은 '{module}'이어야 합니다.")
    refs = request.get("refs", {})
    if not isinstance(refs, dict):
        raise _invalid("refs는 객체여야 합니다.")
    unknown = set(refs) - set(REF_KEYS)
    if unknown:
        raise _invalid("알 수 없는 refs 키가 있습니다.", {"keys": sorted(unknown)})
    _check_ref_formats(refs)
    inp = request.get("input")
    if not isinstance(inp, dict):
        raise _invalid("input은 객체여야 합니다.")
    return refs, inp


def _check_ref_formats(refs):
    bad = []
    if "topic_id" in refs and not ids.is_topic_id(refs["topic_id"]):
        bad.append("topic_id")
    if "content_id" in refs and not ids.is_content_id(refs["content_id"]):
        bad.append("content_id")
    if "discovery_run_id" in refs and (not isinstance(refs["discovery_run_id"], str) or not refs["discovery_run_id"].strip()):
        bad.append("discovery_run_id")
    files = refs.get("drive_file_ids", [])
    if not isinstance(files, list) or any(not isinstance(f, str) or not f.strip() for f in files):
        bad.append("drive_file_ids")
    if bad:
        raise _invalid("refs 값의 형식이 올바르지 않습니다.", {"fields": bad})


def require_refs(refs, *names):
    missing = [n for n in names if not refs.get(n)]
    if missing:
        raise _invalid("필요한 refs가 없습니다.", {"missing": missing})


def _usage(request, meter):
    inp = request.get("input") if isinstance(request, dict) else None
    digest = None
    if isinstance(inp, dict):
        try:
            digest = ids.input_hash({"module": request.get("module"), "input": inp}, config_version())
        except (TypeError, ValueError):
            digest = None
    return meter.to_dict(digest) if meter is not None else ({"input_hash": digest} if digest else {})


def success(request, refs, output, meter=None):
    artifact = output.get("artifact") if isinstance(output, dict) else None
    if isinstance(artifact, dict) and isinstance(artifact.get("content"), str):
        artifact["checksum"] = ids.checksum(artifact["content"])
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": request["run_id"],
        "module": request["module"],
        "refs": refs,
        "output": output,
        "usage": _usage(request, meter),
    }


def failure(request, refs, error, meter=None):
    response = {
        "schema_version": SCHEMA_VERSION,
        "run_id": request.get("run_id") if isinstance(request, dict) else None,
        "module": request.get("module") if isinstance(request, dict) else None,
        "refs": refs,
        "error": error.to_dict(),
    }
    if isinstance(request, dict):
        used = _usage(request, meter)
        if used:
            response["usage"] = used
    return response


def execute(request, module, handler):
    """Validate the request, run `handler(input, refs)` and wrap the result with usage."""
    refs = {}
    meter, token = usage.start()
    try:
        refs, inp = validate_request(request, module)
        return success(request, refs, handler(inp, refs), meter)
    except SkillError as exc:
        return failure(request, refs, exc, meter)
    except Exception:  # noqa: BLE001 - never leak internals or secrets
        return failure(
            request,
            refs,
            SkillError("UNKNOWN_FAILURE", "분류되지 않은 오류가 발생했습니다.", retryable=False),
            meter,
        )
    finally:
        usage.stop(token)


def hash_only(request, module):
    """Validate the envelope and return the `input_hash` a real run would report, without running.

    Lets the workflow check Execution Logs for a reusable result before invoking the module.
    """
    def handler(inp, refs):
        return {"input_hash": _usage(request, None).get("input_hash")}

    response = execute(request, module, handler)
    response.pop("usage", None)
    return response
