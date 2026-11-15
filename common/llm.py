"""Provider-independent LLM access.

An LLM is any callable `llm(role, system, prompt)` returning the response text
or `{"text": str, "usage": {"input_tokens": int, "output_tokens": int}}`;
`role` is a configuration role (e.g. "lightweight", "high_quality"), never a model ID.
Concrete provider adapters are chosen later and injected by the caller.
Adapters should raise `SkillError` with a standard code; otherwise timeouts and
connection errors are mapped to API_TRANSIENT and HTTP 429 to API_RATE_LIMITED.
"""

import json
import re

from common import usage
from common.errors import SkillError, call_provider

MAX_JSON_REPAIRS = 2
_FENCE = re.compile(r"^```[a-zA-Z0-9]*\s*|\s*```$")


def require_llm(llm):
    if llm is None:
        raise SkillError("AUTH_OR_PERMISSION", "AI 공급자가 설정되지 않았습니다.")
    return llm


def extract_json(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("빈 응답입니다.")
    cleaned = _FENCE.sub("", text.strip()).strip()
    starts = [i for i in (cleaned.find("{"), cleaned.find("[")) if i >= 0]
    if not starts:
        raise ValueError("JSON을 찾을 수 없습니다.")
    value, _ = json.JSONDecoder().raw_decode(cleaned[min(starts):])
    return value


def call_json(llm, role, system, prompt, validate=None, max_repairs=MAX_JSON_REPAIRS):
    """Call the model and return validated JSON; repair at most `max_repairs` times."""
    require_llm(llm)
    text = usage.llm_text(call_provider(llm, role, system, prompt))
    last_error = ""
    for attempt in range(max_repairs + 1):
        try:
            data = extract_json(text)
            if validate is not None:
                checked = validate(data)
                data = data if checked is None else checked
            return data
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            last_error = str(exc)
            if attempt == max_repairs:
                break
            repair = (
                f"{prompt}\n\n이전 응답이 규격에 맞지 않습니다: {last_error}\n"
                "설명 없이 올바른 JSON만 다시 출력하세요."
            )
            text = usage.llm_text(call_provider(llm, role, system, repair))
    raise SkillError("INVALID_JSON", "모델 응답이 JSON 규격에 맞지 않습니다.", details={"reason": last_error})


def run_with_quality(produce, check, max_reruns=2):
    """Rerun only the producing step when `check(result)` returns problems."""
    problems = []
    for _ in range(max_reruns + 1):
        result = produce(problems)
        problems = check(result)
        if not problems:
            return result
    raise SkillError(
        "QUALITY_BELOW_THRESHOLD",
        "품질 기준을 충족하지 못했습니다.",
        details={"problems": problems[:10]},
    )
