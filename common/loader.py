"""Load modules from hyphenated folders (skills/topic-discovery, scripts/seo-checker)."""

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_NAME = re.compile(r"[a-z][a-z0-9-]*")


def load_module(kind, name):
    """Load `{kind}/{name}/{name_with_underscores}.py` as an importable module."""
    if kind not in ("skills", "scripts") or not isinstance(name, str) or not _NAME.fullmatch(name):
        raise ModuleNotFoundError(f"{kind}/{name} not found")
    mod_name = f"{kind}_{name.replace('-', '_')}"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    base = (ROOT / kind).resolve()
    path = (base / name / f"{name.replace('-', '_')}.py").resolve()
    if base not in path.parents or not path.is_file():
        raise ModuleNotFoundError(f"{kind}/{name} not found")
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(mod_name, None)
        raise
    return module


def load_skill(name):
    return load_module("skills", name)


def load_script(name):
    return load_module("scripts", name)
