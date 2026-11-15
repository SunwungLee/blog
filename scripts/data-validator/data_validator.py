"""Deterministic JSON validation (subset of JSON Schema) and ID checks."""

import re
import sys
from pathlib import Path

if __name__ == "__main__":  # allow `python scripts/data-validator/data_validator.py`
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.envelope import SCHEMA_VERSION  # noqa: E402
from common.errors import ERROR_CODES  # noqa: E402

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _type_ok(value, expected):
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[expected])


def validate(instance, schema, path="$"):
    """Return a list of error strings; empty means valid.

    Supported keywords: type (str or list), enum, required, properties,
    additionalProperties (bool), items, minItems, maxItems, uniqueItems,
    minLength, maxLength, pattern, minimum, maximum.
    """
    errors = []
    expected = schema.get("type")
    if expected is not None:
        options = expected if isinstance(expected, list) else [expected]
        if not any(_type_ok(instance, t) for t in options):
            return [f"{path}: 타입은 {'/'.join(options)}이어야 합니다."]
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: 허용되지 않은 값입니다.")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{path}: 너무 짧습니다.")
        if len(instance) > schema.get("maxLength", float("inf")):
            errors.append(f"{path}: 너무 깁니다.")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: 형식이 맞지 않습니다.")
    if _type_ok(instance, "number"):
        if instance < schema.get("minimum", float("-inf")):
            errors.append(f"{path}: 최솟값 미만입니다.")
        if instance > schema.get("maximum", float("inf")):
            errors.append(f"{path}: 최댓값 초과입니다.")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{path}: 항목이 너무 적습니다.")
        if len(instance) > schema.get("maxItems", float("inf")):
            errors.append(f"{path}: 항목이 너무 많습니다.")
        if schema.get("uniqueItems") and len({repr(i) for i in instance}) != len(instance):
            errors.append(f"{path}: 중복 항목이 있습니다.")
        if "items" in schema:
            for i, item in enumerate(instance):
                errors.extend(validate(item, schema["items"], f"{path}[{i}]"))
    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}.{key}: 필수 필드가 없습니다.")
        for key, sub in props.items():
            if key in instance:
                errors.extend(validate(instance[key], sub, f"{path}.{key}"))
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in props:
                    errors.append(f"{path}.{key}: 허용되지 않은 필드입니다.")
    return errors


ENVELOPE_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "run_id", "module", "refs"],
    "properties": {
        "schema_version": {"type": "string", "enum": [SCHEMA_VERSION]},
        "run_id": {"type": "string", "minLength": 1},
        "module": {"type": "string", "minLength": 1},
        "refs": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "discovery_run_id": {"type": "string", "minLength": 1},
                "topic_id": {"type": "string", "pattern": r"^TOP-\d{8}-\d{4}\Z"},
                "content_id": {"type": "string", "pattern": r"^CNT-\d{8}-\d{4}\Z"},
                "drive_file_ids": {"type": "array", "items": {"type": "string", "minLength": 1}},
            },
        },
        "input": {"type": "object"},
        "output": {"type": "object"},
        "usage": {"type": "object"},
        "error": {
            "type": "object",
            "required": ["code", "message", "retryable"],
            "properties": {
                "code": {"type": "string", "enum": sorted(ERROR_CODES)},
                "message": {"type": "string"},
                "retryable": {"type": "boolean"},
            },
        },
    },
}


def validate_envelope(message):
    """Validate a request or response; a response needs exactly one of output/error."""
    errors = validate(message, ENVELOPE_SCHEMA)
    if isinstance(message, dict) and "input" not in message:
        has_out, has_err = "output" in message, "error" in message
        if has_out == has_err:
            errors.append("$: 응답에는 output 또는 error 중 하나만 있어야 합니다.")
    return errors


def main(argv=None):
    import json
    import sys

    sys.stdin.reconfigure(encoding="utf-8-sig")
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"valid": False, "errors": ["$: 올바른 JSON이 아닙니다."]}, ensure_ascii=False))
        return 1
    errors = validate_envelope(data)
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
