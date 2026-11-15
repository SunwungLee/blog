"""Serialized date-sequence ID allocation (DATA_SCHEMA.md, Identifier and Time Rules).

Allocates `TOP-YYYYMMDD-NNNN` / `CNT-YYYYMMDD-NNNN` IDs for the workflow. A single
operations PC runs n8n, so an OS file lock serializes concurrent callers. `floor` is
the highest sequence already recorded in Sheets for that kind and date; the counter
never goes below it, so a lost or reset state file cannot cause collisions.
Skills never call this; only the workflow allocates IDs.
"""

import json
import os
import time
from contextlib import contextmanager
from datetime import date as _date
from pathlib import Path

from common import ids
from common.errors import SkillError
from common.loader import ROOT

STATE_ENV = "BLOG_ID_STATE_DIR"
STATE_FILE = "id-sequences.json"
LOCK_FILE = "id-sequences.lock"
MAX_COUNT = 100
MAX_SEQ = 9999
LOCK_TIMEOUT_S = 10.0
_FORMAT = {"topic": ids.topic_id, "content": ids.content_id}

if os.name == "nt":
    import msvcrt

    def _lock(handle):
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock(handle):
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _lock(handle):
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(handle):
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _invalid(message):
    return SkillError("INVALID_INPUT", message)


def _storage(message):
    return SkillError("STORAGE_FAILURE", message)


def _state_dir(state_dir):
    if state_dir is not None:
        return Path(state_dir)
    return Path(os.environ.get(STATE_ENV) or ROOT / "state")


@contextmanager
def _locked(path):
    try:
        handle = open(path, "a+b")
    except OSError:
        raise _storage("ID 발급 잠금 파일을 열 수 없습니다.") from None
    try:
        deadline = time.monotonic() + LOCK_TIMEOUT_S
        while True:
            try:
                _lock(handle)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise _storage("ID 발급 잠금을 얻지 못했습니다.") from None
                time.sleep(0.01)
        try:
            yield
        finally:
            _unlock(handle)
    finally:
        handle.close()


def _read(path):
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise _storage("ID 발급 상태 파일을 읽을 수 없습니다.") from None
    if not isinstance(data, dict) or any(isinstance(v, bool) or not isinstance(v, int) for v in data.values()):
        raise _storage("ID 발급 상태 파일 형식이 올바르지 않습니다.")
    return data


def _write(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _parse_day(day):
    if not isinstance(day, str) or len(day) != 10:
        return None
    try:
        return _date.fromisoformat(day)
    except ValueError:
        return None


def allocate(kind, day, count=1, floor=0, state_dir=None):
    """Reserve `count` consecutive IDs of `kind` ('topic'|'content') for ISO date `day`."""
    if kind not in _FORMAT:
        raise _invalid("kind는 topic 또는 content여야 합니다.")
    parsed = _parse_day(day)
    if parsed is None:
        raise _invalid("date는 YYYY-MM-DD 형식이어야 합니다.")
    for name, value, low, high in (("count", count, 1, MAX_COUNT), ("floor", floor, 0, MAX_SEQ)):
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise _invalid(f"{name}는 {low}~{high} 사이의 정수여야 합니다.")
    folder = _state_dir(state_dir)
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        raise _storage("ID 발급 상태 폴더를 만들 수 없습니다.") from None
    key = f"{kind}:{parsed.strftime('%Y%m%d')}"
    with _locked(folder / LOCK_FILE):
        state = _read(folder / STATE_FILE)
        start = max(state.get(key, 0), floor) + 1
        end = start + count - 1
        if end > MAX_SEQ:
            raise _storage("해당 날짜의 ID 일련번호가 소진되었습니다.")
        state[key] = end
        try:
            _write(folder / STATE_FILE, state)
        except OSError:
            raise _storage("ID 발급 상태를 저장하지 못했습니다.") from None
    return [_FORMAT[kind](parsed, seq) for seq in range(start, end + 1)]
