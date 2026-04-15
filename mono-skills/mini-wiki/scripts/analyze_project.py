#!/usr/bin/env python3
"""
Project structure analyzer for Mini-Wiki.

The analyzer is designed for large front-end and monorepo projects where
documentation quality depends on correct stack detection, workspace awareness,
and stable non-overlapping module boundaries.
"""

import glob
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from config_utils import DEFAULT_FILE_EXCLUDE_PATTERNS, get_effective_excludes, path_matches_patterns

# Directories that should never participate in source analysis.
IGNORE_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "__pycache__",
    ".next",
    ".nuxt",
    "coverage",
    ".nyc_output",
    "vendor",
    "venv",
    ".venv",
    "env",
    ".env",
    "eggs",
    ".eggs",
    ".tox",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".mini-wiki",
    ".agent",
}

IGNORE_FILES = {
    ".DS_Store",
    "Thumbs.db",
    ".gitignore",
    ".gitattributes",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "composer.lock",
}

PROJECT_INDICATORS = {
    "nodejs": ["package.json"],
    "typescript": ["tsconfig.json", "tsconfig.*.json"],
    "python": ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"],
    "go": ["go.mod", "go.sum"],
    "rust": ["Cargo.toml"],
    "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
    "ruby": ["Gemfile"],
    "php": ["composer.json"],
    "dotnet": ["*.csproj", "*.fsproj", "*.sln"],
    "vite": ["vite.config.js", "vite.config.ts", "vite.config.mjs", "vite.config.cjs"],
    "nextjs": ["next.config.js", "next.config.mjs", "next.config.ts"],
    "nuxt": ["nuxt.config.js", "nuxt.config.ts", "nuxt.config.mjs"],
    "vue": ["vue.config.js"],
}

CODE_EXTENSIONS = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".py",
    ".pyi",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".scala",
    ".rb",
    ".php",
    ".cs",
    ".fs",
    ".vue",
    ".svelte",
    ".astro",
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
}

ENTRY_POINT_CANDIDATES = [
    "src/index.ts",
    "src/index.tsx",
    "src/index.js",
    "src/main.ts",
    "src/main.tsx",
    "src/main.js",
    "src/app.tsx",
    "src/App.tsx",
    "src/App.vue",
    "app/page.tsx",
    "pages/index.tsx",
    "pages/index.vue",
    "main.py",
    "app.py",
    "src/main.py",
    "cmd/main.go",
    "main.go",
    "src/main.rs",
    "src/lib.rs",
    "stage/index.tsx",
]

DOC_PATTERNS = [
    "README.md",
    "README.*.md",
    "readme.md",
    "CHANGELOG.md",
    "HISTORY.md",
    "changelog.md",
    "CONTRIBUTING.md",
    "ARCHITECTURE.md",
    "DESIGN.md",
    "API.md",
    "SECURITY.md",
    "LICENSE",
    "LICENSE.md",
    "docs/**/*.md",
    "documentation/**/*.md",
    "src/docs/**/*.md",
]

SOURCE_ROOT_CANDIDATES = [
    "src",
    "stage",
    "kiwi",
    "scripts",
    "types",
    "locales",
    "tailwind",
]

MODULE_SPLIT_THRESHOLD = 100
MIN_CHILD_MODULE_FILES = 4
MIN_CHILDREN_FOR_SPLIT = 3
MAX_PARTITION_DEPTH = 2

EXPORT_PATTERNS = [
    re.compile(r"^\s*export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var|type|interface|enum)\s+", re.MULTILINE),
    re.compile(r"^\s*export\s*\{", re.MULTILINE),
    re.compile(r"^\s*module\.exports\s*=", re.MULTILINE),
    re.compile(r"^\s*exports\.\w+\s*=", re.MULTILINE),
    re.compile(r"^\s*pub\s+(?:fn|struct|enum|trait|type|mod)\s+", re.MULTILINE),
    re.compile(r"^\s*public\s+(?:class|interface|enum)\s+", re.MULTILINE),
    re.compile(r"^\s*def\s+\w+\(", re.MULTILINE),
    re.compile(r"^\s*class\s+\w+", re.MULTILINE),
]


def dedupe(values: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    result: List[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def should_skip_path(path: Path, exclude_dirs: Set[str]) -> bool:
    return any(part in exclude_dirs for part in path.parts)


def is_code_file(path: Path, project_root: Path, exclude_dirs: Set[str], exclude_patterns: Set[str]) -> bool:
    return (
        path.is_file()
        and path.name not in IGNORE_FILES
        and path.suffix in CODE_EXTENSIONS
        and not should_skip_path(path, exclude_dirs)
        and not path_matches_patterns(path, project_root, exclude_patterns)
    )


def scan_code_files(dir_path: Path, project_root: Path, exclude_dirs: Set[str], exclude_patterns: Set[str]) -> List[Path]:
    if not dir_path.exists():
        return []
    return [path for path in dir_path.rglob("*") if is_code_file(path, project_root, exclude_dirs, exclude_patterns)]


def count_exports(content: str) -> int:
    return sum(len(pattern.findall(content)) for pattern in EXPORT_PATTERNS)


def find_workspace_root(root_path: Path) -> Optional[Path]:
    current = root_path.resolve()
    for candidate in [current, *current.parents]:
        package_json = load_json(candidate / "package.json")
        if (candidate / "pnpm-workspace.yaml").exists() or (candidate / "turbo.json").exists():
            return candidate
        workspaces = package_json.get("workspaces")
        if isinstance(workspaces, list):
            return candidate
        if isinstance(workspaces, dict) and workspaces.get("packages"):
            return candidate
    return None


def parse_workspace_patterns(workspace_root: Path) -> List[str]:
    patterns: List[str] = []

    root_package = load_json(workspace_root / "package.json")
    workspaces = root_package.get("workspaces")
    if isinstance(workspaces, list):
        patterns.extend(workspaces)
    elif isinstance(workspaces, dict):
        packages = workspaces.get("packages", [])
        if isinstance(packages, list):
            patterns.extend(packages)

    pnpm_workspace = workspace_root / "pnpm-workspace.yaml"
    if pnpm_workspace.exists():
        try:
            for line in pnpm_workspace.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped.startswith("-"):
                    continue
                patterns.append(stripped.lstrip("-").strip().strip("'\""))
        except OSError:
            pass

    return dedupe(patterns)


def load_workspace_packages(workspace_root: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    if not workspace_root:
        return {}

    selected_dirs: Set[Path] = set()
    patterns = parse_workspace_patterns(workspace_root)
    for pattern in patterns:
        is_negative = pattern.startswith("!")
        normalized = pattern[1:] if is_negative else pattern
        matches = glob.glob(str(workspace_root / normalized), recursive=True)
        package_dirs = set()
        for match in matches:
            raw_path = Path(match)
            package_dir = (raw_path.parent if raw_path.name == "package.json" else raw_path).resolve()
            if should_skip_path(package_dir, IGNORE_DIRS):
                continue
            if not package_dir.joinpath("package.json").exists():
                continue
            package_dirs.add(package_dir)
        if is_negative:
            selected_dirs.difference_update(package_dirs)
        else:
            selected_dirs.update(package_dirs)

    packages: Dict[str, Dict[str, Any]] = {}
    for package_dir in sorted(selected_dirs):
        package_json = load_json(package_dir / "package.json")
        package_name = package_json.get("name")
        if not package_name:
            continue
        try:
            relative_path = str(package_dir.relative_to(workspace_root))
        except ValueError:
            relative_path = str(package_dir)
        packages[package_name] = {
            "name": package_name,
            "path": relative_path,
            "private": bool(package_json.get("private", False)),
        }
    return packages


def detect_package_manager(root_path: Path) -> List[str]:
    managers = []
    if (root_path / "package-lock.json").exists():
        managers.append("npm")
    if (root_path / "yarn.lock").exists():
        managers.append("yarn")
    if (root_path / "pnpm-lock.yaml").exists():
        managers.append("pnpm")
    if (root_path / "bun.lockb").exists():
        managers.append("bun")
    return managers


def detect_monorepo_tools(workspace_root: Optional[Path]) -> List[str]:
    if not workspace_root:
        return []

    tools = []
    if (workspace_root / "pnpm-workspace.yaml").exists():
        tools.extend(["pnpm-workspaces", "monorepo"])
    if (workspace_root / "lerna.json").exists():
        tools.extend(["lerna", "monorepo"])
    if (workspace_root / "turbo.json").exists():
        tools.extend(["turborepo", "monorepo"])

    root_package = load_json(workspace_root / "package.json")
    workspaces = root_package.get("workspaces")
    if isinstance(workspaces, (list, dict)):
        tools.append("workspace")
        tools.append("monorepo")

    return dedupe(tools)


def has_native_bridge(root_path: Path) -> Tuple[bool, bool]:
    native_files = [
        path
        for path in root_path.rglob("*")
        if path.suffix in {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"}
        and not should_skip_path(path, IGNORE_DIRS)
    ]
    has_native = bool(native_files)
    has_wasm = has_native and (
        (root_path / "build.sh").exists()
        or any(path.name == "CMakeLists.txt" for path in root_path.rglob("CMakeLists.txt"))
    )
    return has_native, has_wasm


def detect_project_types(root_path: Path, workspace_root: Optional[Path] = None) -> List[str]:
    detected: List[str] = []

    for project_type, indicators in PROJECT_INDICATORS.items():
        for indicator in indicators:
            if "*" in indicator:
                if list(root_path.glob(indicator)):
                    detected.append(project_type)
                    break
            elif (root_path / indicator).exists():
                detected.append(project_type)
                break

    detected.extend(detect_package_manager(root_path))
    detected.extend(detect_monorepo_tools(workspace_root))

    package_json = load_json(root_path / "package.json")
    dependencies = {
        **package_json.get("dependencies", {}),
        **package_json.get("devDependencies", {}),
        **package_json.get("peerDependencies", {}),
    }

    if dependencies:
        if "react" in dependencies or "@vitejs/plugin-react" in dependencies:
            detected.append("react")
        if "vue" in dependencies or "@vitejs/plugin-vue" in dependencies:
            detected.append("vue")
        if "next" in dependencies:
            detected.append("nextjs")
        if "vite" in dependencies or any((root_path / name).exists() for name in ("vite.config.ts", "vite.config.js", "vite.config.mjs", "vite.config.cjs")):
            detected.append("vite")
        if "vitest" in dependencies:
            detected.append("vitest")
        if "tailwindcss" in dependencies:
            detected.append("tailwind")
        if "zustand" in dependencies:
            detected.append("zustand")
        if "rxjs" in dependencies:
            detected.append("rxjs")
        if "i18next" in dependencies:
            detected.append("i18n")

    if not dependencies:
        if list(root_path.rglob("*.tsx")):
            detected.append("react")
        if list(root_path.rglob("*.vue")):
            detected.append("vue")

    has_native, has_wasm = has_native_bridge(root_path)
    if has_native:
        detected.append("cpp")
        detected.append("native-bridge")
    if has_wasm:
        detected.append("wasm")

    pyproject_path = root_path / "pyproject.toml"
    if pyproject_path.exists():
        try:
            import tomllib  # type: ignore[attr-defined]
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ImportError:
                tomllib = None
        if tomllib:
            try:
                with open(pyproject_path, "rb") as handle:
                    pyproject = tomllib.load(handle)
                build_backend = pyproject.get("build-system", {}).get("build-backend", "")
                if "poetry" in build_backend:
                    detected.append("poetry")
            except Exception:
                pass

    if not detected and any(root_path.glob("*.py")):
        detected.append("python")

    return dedupe(detected)


def find_entry_points(root_path: Path) -> List[str]:
    return [entry for entry in ENTRY_POINT_CANDIDATES if (root_path / entry).exists()]


def collect_source_stats(
    dir_path: Path,
    project_root: Path,
    exclude_dirs: Set[str],
    exclude_patterns: Set[str],
    cache: Dict[str, Dict[str, int]],
) -> Dict[str, int]:
    key = str(dir_path.resolve())
    if key in cache:
        return cache[key]

    files = scan_code_files(dir_path, project_root, exclude_dirs, exclude_patterns)
    total_lines = 0
    total_exports = 0
    total_classes = 0
    total_interfaces = 0
    for file_path in files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        total_lines += len(content.splitlines())
        total_exports += count_exports(content)
        total_classes += len(re.findall(r"^\s*(?:export\s+)?class\s+\w+", content, re.MULTILINE))
        total_interfaces += len(re.findall(r"^\s*(?:export\s+)?interface\s+\w+", content, re.MULTILINE))
        total_interfaces += len(re.findall(r"^\s*(?:export\s+)?type\s+\w+\s*=", content, re.MULTILINE))

    stats = {
        "source_files": len(files),
        "source_lines": total_lines,
        "export_count": total_exports,
        "class_count": total_classes,
        "interface_count": total_interfaces,
    }
    cache[key] = stats
    return stats


def detect_module_boundaries(dir_path: Path) -> Dict[str, Any]:
    index_candidates = ["index.ts", "index.tsx", "index.js", "index.jsx"]
    for candidate in index_candidates:
        index_path = dir_path / candidate
        if not index_path.exists():
            continue
        try:
            content = index_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            content = ""
        return {
            "has_index": True,
            "index_file": candidate,
            "estimated_exports": count_exports(content),
        }
    return {"has_index": False, "index_file": None, "estimated_exports": 0}


def calculate_module_importance(module: Dict[str, Any], entry_points: Optional[List[str]] = None) -> float:
    entry_points = entry_points or []
    score = 0.0

    module_path = module.get("path", "")
    for entry_point in entry_points:
        if entry_point.startswith(module_path + "/") or entry_point == module_path:
            score += 5
            break

    score += min(module.get("export_count", 0), 25) * 1.2
    score += min(module.get("source_files", 0), 80) / 20
    score += min(module.get("source_lines", 0), 2000) / 400
    if module.get("has_docs"):
        score += 2
    if module.get("doc_role") == "overview":
        score += 1

    module["importance"] = round(score, 2)
    return score


def slugify_module_path(module_path: str) -> str:
    normalized = module_path.replace("\\", "/")
    if normalized.startswith("src/"):
        normalized = normalized[4:]
    return normalized


def categorize_module(name: str) -> str:
    value = name.lower()
    if any(token in value for token in ("workflow", "flow", "editor", "canvas")):
        return "workflow"
    if any(token in value for token in ("event", "bus", "emitter", "rxjs", "observable")):
        return "event"
    if any(token in value for token in ("store", "state", "slice", "zustand", "redux")):
        return "state"
    if any(token in value for token in ("cloud", "agent", "ai", "chat", "llm")):
        return "ai"
    if any(token in value for token in ("media", "video", "audio", "ffmpeg", "konva")):
        return "media"
    if "hook" in value:
        return "hooks"
    if any(token in value for token in ("route", "router", "page")):
        return "routing"
    if value in {"type", "types", "interface", "interfaces"}:
        return "types"
    if any(token in value for token in ("component", "ui", "view", "widget")):
        return "ui"
    if any(token in value for token in ("api", "service", "handler")):
        return "api"
    if any(token in value for token in ("util", "helper", "common", "shared")):
        return "utility"
    if any(token in value for token in ("core", "lib", "engine")):
        return "core"
    if any(token in value for token in ("config", "setting")):
        return "config"
    if any(token in value for token in ("test", "spec")):
        return "test"
    return "module"


def list_source_roots(root_path: Path, exclude_dirs: Set[str], exclude_patterns: Set[str]) -> List[Path]:
    source_roots: List[Path] = []
    for name in SOURCE_ROOT_CANDIDATES:
        candidate = root_path / name
        if candidate.exists() and candidate.is_dir() and scan_code_files(candidate, root_path, exclude_dirs, exclude_patterns):
            source_roots.append(candidate)

    if not source_roots:
        for child in sorted(root_path.iterdir()):
            if (
                child.is_dir()
                and child.name not in exclude_dirs
                and not child.name.startswith(".")
                and scan_code_files(child, root_path, exclude_dirs, exclude_patterns)
            ):
                source_roots.append(child)

    return dedupe(str(path) for path in source_roots) and [Path(path) for path in dedupe(str(path) for path in source_roots)]


def build_module(
    dir_path: Path,
    root_path: Path,
    entry_points: List[str],
    exclude_dirs: Set[str],
    exclude_patterns: Set[str],
    stats_cache: Dict[str, Dict[str, int]],
    doc_role: str = "module",
    child_modules: Optional[List[str]] = None,
) -> Dict[str, Any]:
    relative_path = str(dir_path.relative_to(root_path))
    stats = collect_source_stats(dir_path, root_path, exclude_dirs, exclude_patterns, stats_cache)
    boundaries = detect_module_boundaries(dir_path)
    has_docs = any((dir_path / name).exists() for name in ("README.md", "readme.md"))

    module = {
        "name": slugify_module_path(relative_path),
        "path": relative_path,
        "slug": slugify_module_path(relative_path),
        "module_type": categorize_module(relative_path),
        "doc_role": doc_role,
        "children": child_modules or [],
        "has_docs": has_docs,
        "has_index": boundaries["has_index"],
        "index_file": boundaries["index_file"],
        "estimated_exports": boundaries["estimated_exports"],
        **stats,
    }
    calculate_module_importance(module, entry_points)
    return module


def should_split_module(
    dir_path: Path,
    root_path: Path,
    exclude_dirs: Set[str],
    exclude_patterns: Set[str],
    stats_cache: Dict[str, Dict[str, int]],
) -> bool:
    stats = collect_source_stats(dir_path, root_path, exclude_dirs, exclude_patterns, stats_cache)
    if stats["source_files"] < MODULE_SPLIT_THRESHOLD:
        return False

    child_dirs = [
        child
        for child in sorted(dir_path.iterdir())
        if child.is_dir()
        and child.name not in exclude_dirs
        and not child.name.startswith(".")
        and collect_source_stats(child, root_path, exclude_dirs, exclude_patterns, stats_cache)["source_files"] >= MIN_CHILD_MODULE_FILES
    ]
    return len(child_dirs) >= MIN_CHILDREN_FOR_SPLIT


def partition_module_tree(
    dir_path: Path,
    root_path: Path,
    entry_points: List[str],
    exclude_dirs: Set[str],
    exclude_patterns: Set[str],
    stats_cache: Dict[str, Dict[str, int]],
    depth: int = 0,
) -> List[Dict[str, Any]]:
    child_dirs = [
        child
        for child in sorted(dir_path.iterdir())
        if child.is_dir()
        and child.name not in exclude_dirs
        and not child.name.startswith(".")
        and collect_source_stats(child, root_path, exclude_dirs, exclude_patterns, stats_cache)["source_files"] >= MIN_CHILD_MODULE_FILES
    ]

    if depth >= MAX_PARTITION_DEPTH or not should_split_module(dir_path, root_path, exclude_dirs, exclude_patterns, stats_cache):
        return [build_module(dir_path, root_path, entry_points, exclude_dirs, exclude_patterns, stats_cache)]

    child_modules: List[Dict[str, Any]] = []
    for child in child_dirs:
        child_modules.extend(
            partition_module_tree(child, root_path, entry_points, exclude_dirs, exclude_patterns, stats_cache, depth + 1)
        )

    overview = build_module(
        dir_path,
        root_path,
        entry_points,
        exclude_dirs,
        exclude_patterns,
        stats_cache,
        doc_role="overview",
        child_modules=[module["slug"] for module in child_modules],
    )
    return [overview, *child_modules]


def discover_modules(root_path: Path, exclude_dirs: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    exclude_dirs = exclude_dirs or IGNORE_DIRS
    _, exclude_patterns = get_effective_excludes(root_path, exclude_dirs, DEFAULT_FILE_EXCLUDE_PATTERNS)
    entry_points = find_entry_points(root_path)
    stats_cache: Dict[str, Dict[str, int]] = {}
    modules: List[Dict[str, Any]] = []

    for source_root in list_source_roots(root_path, exclude_dirs, exclude_patterns):
        if source_root.name == "src":
            child_dirs = [
                child
                for child in sorted(source_root.iterdir())
                if child.is_dir()
                and child.name not in exclude_dirs
                and not child.name.startswith(".")
                and collect_source_stats(child, root_path, exclude_dirs, exclude_patterns, stats_cache)["source_files"] > 0
            ]
            for child in child_dirs:
                modules.extend(partition_module_tree(child, root_path, entry_points, exclude_dirs, exclude_patterns, stats_cache))
        else:
            modules.extend(partition_module_tree(source_root, root_path, entry_points, exclude_dirs, exclude_patterns, stats_cache))

    deduped: Dict[str, Dict[str, Any]] = {}
    for module in modules:
        existing = deduped.get(module["path"])
        if not existing or existing.get("doc_role") == "module" and module.get("doc_role") == "overview":
            deduped[module["path"]] = module

    result = sorted(deduped.values(), key=lambda module: module.get("importance", 0), reverse=True)
    return result


def classify_document(path: Path, root_path: Path) -> Dict[str, Any]:
    relative_path = str(path.relative_to(root_path))
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        content = ""

    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else path.stem

    score = 50
    kind = "reference"
    lower_content = content.lower()
    lower_relative = relative_path.lower()

    if lower_relative.startswith("docs/") or lower_relative.startswith("src/docs/"):
        score += 25
        kind = "design-doc"
    if any(token in lower_relative for token in ("technical-design", "architecture", "design", "streaming", "sdk-events")):
        score += 20
    if path.name.lower() == "readme.md":
        kind = "readme"
        score += 5
        if "template provides a minimal setup" in lower_content or title.lower().startswith("react + typescript + vite"):
            kind = "template-readme"
            score -= 40
    if lower_relative.endswith("license") or lower_relative.endswith("license.md"):
        kind = "license"
        score -= 20

    return {
        "path": relative_path,
        "title": title,
        "kind": kind,
        "trust_score": score,
    }


def find_documentation(root_path: Path) -> List[Dict[str, Any]]:
    docs: Dict[str, Dict[str, Any]] = {}
    for pattern in DOC_PATTERNS:
        for path in root_path.glob(pattern):
            if not path.is_file():
                continue
            relative_path = str(path.relative_to(root_path))
            docs[relative_path.lower()] = classify_document(path, root_path)
    return sorted(docs.values(), key=lambda item: (-item["trust_score"], item["path"]))


def collect_internal_dependencies(root_path: Path, workspace_packages: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    package_json = load_json(root_path / "package.json")
    dependencies = {
        **package_json.get("dependencies", {}),
        **package_json.get("devDependencies", {}),
        **package_json.get("peerDependencies", {}),
    }

    internal_deps: List[Dict[str, Any]] = []
    for name, version in dependencies.items():
        if not isinstance(version, str):
            continue
        if version.startswith("workspace:") or name in workspace_packages:
            metadata = workspace_packages.get(name, {})
            internal_deps.append(
                {
                    "name": name,
                    "version": version,
                    "path": metadata.get("path"),
                }
            )
    return sorted(internal_deps, key=lambda item: item["name"])


def analyze_project(project_root: str, save_to_cache: bool = True) -> Dict[str, Any]:
    root = Path(project_root).resolve()
    workspace_root = find_workspace_root(root)
    workspace_packages = load_workspace_packages(workspace_root)
    exclude_dirs, exclude_patterns = get_effective_excludes(root, IGNORE_DIRS, DEFAULT_FILE_EXCLUDE_PATTERNS)

    project_types = detect_project_types(root, workspace_root)
    entry_points = find_entry_points(root)
    modules = discover_modules(root, exclude_dirs)
    docs_catalog = find_documentation(root)
    docs_found = [doc["path"] for doc in docs_catalog]
    code_files = scan_code_files(root, root, exclude_dirs, exclude_patterns)
    internal_dependencies = collect_internal_dependencies(root, workspace_packages)

    project_stats = {
        "total_files": len(code_files),
        "total_modules": len(modules),
        "total_docs": len(docs_found),
        "source_lines": sum(module["source_lines"] for module in modules if module.get("doc_role") == "module"),
        "export_count": sum(module.get("export_count", module.get("estimated_exports", 0)) for module in modules if module.get("doc_role") == "module"),
        "class_count": sum(module.get("class_count", 0) for module in modules if module.get("doc_role") == "module"),
        "interface_count": sum(module.get("interface_count", 0) for module in modules if module.get("doc_role") == "module"),
    }

    result = {
        "project_name": root.name,
        "project_root": str(root),
        "workspace_root": str(workspace_root) if workspace_root else None,
        "project_type": project_types,
        "entry_points": entry_points,
        "modules": modules,
        "docs_found": docs_found,
        "docs_catalog": docs_catalog,
        "internal_dependencies": internal_dependencies,
        "workspace_packages": workspace_packages,
        "stats": project_stats,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }

    if save_to_cache:
        wiki_dir = root / ".mini-wiki"
        if wiki_dir.exists():
            cache_path = wiki_dir / "cache" / "structure.json"
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    return result


def print_analysis(result: Dict[str, Any]) -> None:
    print(f"📁 项目: {result['project_name']}")
    print(f"🔧 技术栈: {', '.join(result['project_type']) or '未知'}")
    print(
        f"📊 统计: {result['stats']['total_files']} 个代码文件, "
        f"{result['stats']['total_modules']} 个模块, "
        f"{result['stats']['total_docs']} 个文档"
    )

    if result.get("workspace_root"):
        print(f"🏢 Workspace: {result['workspace_root']}")

    if result["entry_points"]:
        print("\n🚀 入口文件:")
        for entry in result["entry_points"]:
            print(f"  - {entry}")

    if result["modules"]:
        print("\n📦 模块:")
        for module in result["modules"][:20]:
            overview_flag = " [概览]" if module.get("doc_role") == "overview" else ""
            print(
                f"  - {module['slug']} "
                f"({module['source_files']} 个文件, {module['module_type']}, "
                f"{module['source_lines']} 行, ⭐{module.get('importance', 0)})"
                f"{overview_flag}"
            )

    if result["internal_dependencies"]:
        print("\n🔗 内部依赖:")
        for dependency in result["internal_dependencies"][:10]:
            target = dependency.get("path") or "未解析"
            print(f"  - {dependency['name']} -> {target}")

    if result["docs_catalog"]:
        print("\n📄 现有文档:")
        for doc in result["docs_catalog"][:10]:
            print(f"  - {doc['path']} ({doc['kind']}, score={doc['trust_score']})")


if __name__ == "__main__":
    import sys

    project_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    analysis = analyze_project(project_path, save_to_cache=False)
    print_analysis(analysis)
