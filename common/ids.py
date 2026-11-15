"""Stable identifiers and Drive file names (DATA_SCHEMA.md).

Sequence allocation is serialized by the workflow; these helpers only format
and validate. Skills never invent IDs.
"""

import hashlib
import json
import re
import uuid

TOPIC_ID_RE = re.compile(r"TOP-\d{8}-\d{4}")
CONTENT_ID_RE = re.compile(r"CNT-\d{8}-\d{4}")
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)


def _format(prefix, date, seq):
    if not 1 <= seq <= 9999:
        raise ValueError("sequence must be 1..9999")
    return f"{prefix}-{date.strftime('%Y%m%d')}-{seq:04d}"


def topic_id(date, seq):
    return _format("TOP", date, seq)


def content_id(date, seq):
    return _format("CNT", date, seq)


def new_uuid():
    return str(uuid.uuid4())


def is_topic_id(value):
    return isinstance(value, str) and bool(TOPIC_ID_RE.fullmatch(value))


def is_content_id(value):
    return isinstance(value, str) and bool(CONTENT_ID_RE.fullmatch(value))


def is_uuid(value):
    return isinstance(value, str) and bool(UUID_RE.fullmatch(value))


def input_hash(payload, config_version=""):
    """Deterministic cache key for a skill input (TOKEN_OPTIMIZATION.md)."""
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{config_version}\n{canonical}".encode("utf-8")).hexdigest()


def checksum(content):
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def file_name(cid, artifact_type, version, ext):
    if not is_content_id(cid):
        raise ValueError("invalid content_id")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", artifact_type):
        raise ValueError("invalid artifact_type")
    if version < 1:
        raise ValueError("version must be >= 1")
    return f"{cid}_{artifact_type}_v{version:03d}.{ext.lstrip('.')}"


SUBFOLDERS = {
    "research": "research",
    "plan": "plans",
    "master": "articles",
    "final": "articles",
    "image": "images",
    "naver": "publishing/naver",
    "blogspot": "publishing/blogspot",
}


def drive_path(cid, artifact_type):
    return f"content/{cid}/{SUBFOLDERS.get(artifact_type, 'articles')}"
