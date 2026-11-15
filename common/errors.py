"""Canonical error codes (Phase_0_design.md section 9.2)."""

ERROR_CODES = {
    "API_TRANSIENT",
    "API_RATE_LIMITED",
    "INVALID_JSON",
    "QUALITY_BELOW_THRESHOLD",
    "INSUFFICIENT_EVIDENCE",
    "INVALID_INPUT",
    "STORAGE_FAILURE",
    "AUTH_OR_PERMISSION",
    "UNKNOWN_FAILURE",
}

RETRYABLE_CODES = {"API_TRANSIENT", "API_RATE_LIMITED"}


class SkillError(Exception):
    """Structured failure that maps to the response envelope's `error` object."""

    def __init__(self, code, message, retryable=None, details=None):
        if code not in ERROR_CODES:
            raise ValueError(f"unknown error code: {code}")
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = code in RETRYABLE_CODES if retryable is None else retryable
        self.details = details

    def to_dict(self):
        err = {"code": self.code, "message": self.message, "retryable": self.retryable}
        if self.details:
            err["details"] = self.details
        return err


def from_provider_exception(exc, provider="AI"):
    """Map an adapter exception to a standard code without exposing its message.

    Adapters may raise SkillError directly; otherwise timeouts/connection errors
    become API_TRANSIENT and HTTP 429 becomes API_RATE_LIMITED (section 9.2).
    """
    if isinstance(exc, SkillError):
        return exc
    status = getattr(exc, "status", None) or getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if status == 429:
        return SkillError("API_RATE_LIMITED", f"{provider} 공급자 호출 한도를 초과했습니다.")
    if status in (401, 403):
        return SkillError("AUTH_OR_PERMISSION", f"{provider} 공급자 인증 또는 권한 오류입니다.")
    if isinstance(status, int) and status >= 500:
        return SkillError("API_TRANSIENT", f"{provider} 공급자 서버 오류입니다.")
    if isinstance(exc, (TimeoutError, ConnectionError)) or type(exc).__name__ in ("URLError", "RemoteDisconnected", "IncompleteRead"):
        return SkillError("API_TRANSIENT", f"{provider} 공급자 연결이 일시적으로 실패했습니다.")
    return None


def call_provider(fn, *args, provider="AI"):
    """Invoke an injected provider callable and normalize its failures."""
    try:
        return fn(*args)
    except Exception as exc:  # noqa: BLE001 - re-raised as a standard code below
        mapped = from_provider_exception(exc, provider)
        if mapped is None:
            raise
        raise mapped from None
