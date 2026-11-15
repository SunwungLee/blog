"""Load JSON settings from config/ (YAML can replace this once PyYAML is installed)."""

import json

from common.loader import ROOT

_cache = {}


def load(name):
    if name not in _cache:
        path = ROOT / "config" / f"{name}.json"
        _cache[name] = json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else {}
    return _cache[name]


def config_version():
    """Combined version of the applied config files, used in `input_hash`."""
    names = ("model-config", "quality-rules", "writing-style")
    return "|".join(f"{n}:{load(n).get('version', '')}" for n in names)


def quality(key, default):
    """Provisional quality thresholds from config/quality-rules.json."""
    return load("quality-rules").get(key, default)


def role_for(task, default):
    """Model role for a task from config/model-config.json (`tasks.<task>.model`), never a model ID."""
    tasks = load("model-config").get("tasks", {})
    entry = tasks.get(task) if isinstance(tasks, dict) else None
    role = entry.get("model") if isinstance(entry, dict) else entry
    return role if isinstance(role, str) and role.strip() else default


def style_prompt(override=None):
    """Writing-style instructions for prompts; a caller override replaces the tone only."""
    cfg = load("writing-style")
    tone = override or cfg.get("tone", "")
    rules = "\n".join(f"- {r}" for r in cfg.get("rules", []))
    return f"문체: {tone}\n{rules}".strip()


def forbidden_phrases():
    return list(load("writing-style").get("forbidden_phrases", []))
