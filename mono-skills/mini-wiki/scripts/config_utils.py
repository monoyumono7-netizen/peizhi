#!/usr/bin/env python3
"""
Shared configuration helpers for Mini-Wiki scripts.
"""

from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


DEFAULT_FILE_EXCLUDE_PATTERNS: Set[str] = {
    "*.test.ts",
    "*.test.tsx",
    "*.spec.ts",
    "*.spec.tsx",
    "*.test.js",
    "*.spec.js",
    "*.bak",
}


def load_yaml_file(path: Path) -> Dict[str, Any]:
    if not path.exists() or yaml is None:
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def load_project_config(project_root: Path) -> Dict[str, Any]:
    return load_yaml_file(project_root / ".mini-wiki" / "config.yaml")


def split_excludes(
    configured: Sequence[Any],
    default_dirs: Iterable[str],
    default_patterns: Iterable[str],
) -> Tuple[Set[str], Set[str]]:
    exclude_dirs = set(default_dirs)
    exclude_patterns = set(default_patterns)

    for item in configured:
        if not isinstance(item, str):
            continue
        value = item.strip()
        if not value:
            continue
        if any(token in value for token in ("*", "?", "[", "]", "/")):
            exclude_patterns.add(value)
        else:
            exclude_dirs.add(value)

    return exclude_dirs, exclude_patterns


def get_effective_excludes(
    project_root: Path,
    default_dirs: Iterable[str],
    default_patterns: Iterable[str],
) -> Tuple[Set[str], Set[str]]:
    config = load_project_config(project_root)
    configured = config.get("exclude", [])
    if not isinstance(configured, list):
        configured = []
    return split_excludes(configured, default_dirs, default_patterns)


def path_matches_patterns(path: Path, project_root: Path, patterns: Iterable[str]) -> bool:
    try:
        relative = path.relative_to(project_root).as_posix()
    except ValueError:
        relative = path.as_posix()

    for pattern in patterns:
        if fnmatch(path.name, pattern) or fnmatch(relative, pattern):
            return True
    return False
