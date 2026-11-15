"""Run one skill: `python run_skill.py <skill-name> [--providers module] [--hash-only] < request.json > response.json`.

The providers module (chosen later, kept out of the repo) may expose `llm` and `search`
callables; without it AI/search skills return a structured AUTH_OR_PERMISSION error.
`--hash-only` validates the envelope and returns `output.input_hash` without running the
skill, so the workflow can reuse an earlier successful result (ORCHESTRATION_FOUNDATION.md).
Every outcome is a JSON envelope on stdout: exit code 0 = `output`, 1 = `error`.
"""

import argparse
import importlib
import inspect
import json
import sys

from common.errors import SkillError
from common.envelope import failure, hash_only
from common.loader import load_skill


def read_request():
    """Read a JSON request from stdin (UTF-8, BOM tolerated); return (request, error_response)."""
    sys.stdin.reconfigure(encoding="utf-8-sig")
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        return json.load(sys.stdin), None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, failure({}, {}, SkillError("INVALID_INPUT", "요청이 올바른 JSON이 아닙니다."))


def emit(response):
    print(json.dumps(response, ensure_ascii=False))
    return 0 if "output" in response else 1


def load_failure(request):
    """Envelope for a module that exists but cannot be loaded; never echoes the exception."""
    return failure(request, {}, SkillError("UNKNOWN_FAILURE", "모듈을 불러오지 못했습니다.", retryable=False))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("skill")
    parser.add_argument("--providers", help="importable module exposing llm/search callables")
    parser.add_argument("--hash-only", action="store_true", help="return input_hash without running the skill")
    args = parser.parse_args(argv)
    request, error = read_request()
    if error:
        return emit(error)
    try:
        skill = load_skill(args.skill)
    except ModuleNotFoundError:
        return emit(failure(request, {}, SkillError("INVALID_INPUT", "알 수 없는 skill입니다.")))
    except Exception:  # noqa: BLE001 - a broken module must still answer with an envelope
        return emit(load_failure(request))
    if args.hash_only:
        return emit(hash_only(request, args.skill))
    kwargs = {}
    if args.providers:
        try:
            providers = importlib.import_module(args.providers)
        except Exception:  # noqa: BLE001 - provider modules may hold secrets; never echo their errors
            return emit(failure(request, {}, SkillError("AUTH_OR_PERMISSION", "공급자 모듈을 불러올 수 없습니다.")))
        accepted = inspect.signature(skill.run).parameters
        kwargs = {k: getattr(providers, k) for k in ("llm", "search") if k in accepted and hasattr(providers, k)}
    return emit(skill.run(request, **kwargs))


if __name__ == "__main__":
    raise SystemExit(main())
