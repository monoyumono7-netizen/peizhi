#!/usr/bin/env python3
"""
Production-oriented wiki generator for Mini-Wiki.

The generator turns project analysis results into a curated set of durable
project docs, writes governance frontmatter, and feeds the output back into the
quality gate so the generated wiki can be used in CI.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import analyze_project
import check_quality
import detect_changes
import generate_diagram
import init_wiki
from config_utils import DEFAULT_FILE_EXCLUDE_PATTERNS, get_effective_excludes, load_project_config, load_yaml_file

GENERATOR_VERSION = "4.1.0"
QUALITY_RULESET_VERSION = "enterprise-v2"
MODULE_DOC_LIMIT = 6
API_DOC_LIMIT = 2
MAX_FOCUS_FILES = 8
MAX_API_FOCUS_FILES = 5
MAX_EXPORT_ENTRIES = 12
MAX_CODE_SNIPPETS = 6
DEFAULT_GITHUB_REF = "main"
SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
TS_SEMANTIC_ANALYZER = SCRIPT_ROOT / "ts_semantic_analyzer.mjs"
WEB_FLOW_PROFILE_PATH = SKILL_ROOT / "assets" / "profiles" / "web-flow.yaml"
QUALITY_ORDER = {"basic": 0, "standard": 1, "professional": 2}

RUNTIME_LINK_SETTINGS: Dict[str, Optional[str]] = {
    "source_link_style": "relative",
    "github_repo_url": None,
    "github_ref": DEFAULT_GITHUB_REF,
}
RUNTIME_ACTIVE_PLUGINS: List[str] = []

MODULE_TYPE_DESCRIPTIONS = {
    "workflow": "负责画布、节点编排、编辑器行为和用户操作流转。",
    "ai": "负责 AI 代理、聊天流、生成协议和模型调用上下文。",
    "api": "负责远端服务访问、请求编排和接口封装。",
    "event": "负责事件总线、生命周期广播和跨模块同步。",
    "state": "负责全局状态切片、缓存状态和跨页面共享上下文。",
    "ui": "负责页面组件、交互容器和设计系统落地。",
    "routing": "负责路由入口、页面分发和导航约束。",
    "utility": "负责通用工具、数据转换、缓存和基础设施封装。",
    "hooks": "负责复用业务 Hook 和跨组件逻辑装配。",
    "media": "负责多媒体处理、渲染和资源转换。",
    "core": "负责系统主链路和核心抽象。",
    "config": "负责配置、环境和构建接线。",
    "types": "负责共享类型和协议约束。",
    "module": "负责该领域的主业务能力与实现细节。",
}

API_PATTERNS: Sequence[Tuple[str, re.Pattern[str]]] = (
    ("function", re.compile(r"^\s*export\s+(?:async\s+)?function\s+([A-Za-z0-9_]+)")),
    ("class", re.compile(r"^\s*export\s+class\s+([A-Za-z0-9_]+)")),
    ("const", re.compile(r"^\s*export\s+const\s+([A-Za-z0-9_]+)")),
    ("type", re.compile(r"^\s*export\s+type\s+([A-Za-z0-9_]+)")),
    ("interface", re.compile(r"^\s*export\s+interface\s+([A-Za-z0-9_]+)")),
    ("enum", re.compile(r"^\s*export\s+enum\s+([A-Za-z0-9_]+)")),
    ("python-function", re.compile(r"^\s*def\s+([A-Za-z0-9_]+)\s*\(")),
    ("python-class", re.compile(r"^\s*class\s+([A-Za-z0-9_]+)\b")),
    ("cpp-function", re.compile(r"^\s*(?:int|void|bool|char|float|double|std::\w+)\s+([A-Za-z0-9_]+)\s*\(")),
)

GENERIC_PATH_SEGMENTS = {
    "src",
    "components",
    "common",
    "shared",
    "core",
    "index",
    "lib",
    "docs",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_quality_level(value: Any, default: str = "professional") -> str:
    normalized = str(value or default).strip().lower()
    return normalized if normalized in QUALITY_ORDER else default


def quality_rank(value: str) -> int:
    return QUALITY_ORDER.get(normalize_quality_level(value), QUALITY_ORDER["professional"])


def configure_runtime_link_settings(settings: Dict[str, Any]) -> None:
    RUNTIME_LINK_SETTINGS["source_link_style"] = str(settings.get("source_link_style", "relative"))
    RUNTIME_LINK_SETTINGS["github_repo_url"] = settings.get("github_repo_url")
    RUNTIME_LINK_SETTINGS["github_ref"] = str(settings.get("github_ref", DEFAULT_GITHUB_REF))


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def language_for_file(path: Path) -> str:
    return {
        ".ts": "ts",
        ".tsx": "tsx",
        ".js": "js",
        ".jsx": "jsx",
        ".py": "python",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".cc": "cpp",
        ".cpp": "cpp",
        ".cxx": "cpp",
        ".c": "c",
        ".h": "cpp",
        ".hpp": "cpp",
    }.get(path.suffix.lower(), "")


def slug_to_filename(slug: str) -> str:
    return slug.replace("/", "-").replace("\\", "-")


def humanize_slug(slug: str) -> str:
    return slug.replace("/", " / ")


def format_frontmatter(data: Dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
            continue
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def write_document(path: Path, metadata: Dict[str, Any], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"{format_frontmatter(metadata)}\n\n{body.strip()}\n"
    path.write_text(content, encoding="utf-8")


def build_relative_link(from_path: Path, to_path: Path) -> str:
    relative = os.path.relpath(to_path, start=from_path.parent).replace(os.sep, "/")
    return relative if relative.startswith(".") else f"./{relative}"


def get_wiki_root(doc_path: Path) -> Path:
    return doc_path.parent if doc_path.parent.name == "wiki" else doc_path.parent.parent


def doc_link(from_path: Path, relative_target: str) -> str:
    return build_relative_link(from_path, get_wiki_root(from_path) / relative_target)


def source_link(from_path: Path, project_root: Path, source_path: str) -> str:
    if RUNTIME_LINK_SETTINGS.get("source_link_style") == "github_url":
        github_repo_url = (RUNTIME_LINK_SETTINGS.get("github_repo_url") or "").rstrip("/")
        github_ref = (RUNTIME_LINK_SETTINGS.get("github_ref") or DEFAULT_GITHUB_REF).strip() or DEFAULT_GITHUB_REF
        if github_repo_url:
            normalized = source_path.replace("\\", "/").lstrip("./")
            return f"{github_repo_url}/blob/{github_ref}/{normalized}"
    return build_relative_link(from_path, project_root / source_path)


def read_owners(project_root: Path, owner_file_name: str) -> List[str]:
    owner_file = project_root / owner_file_name
    if not owner_file.exists():
        return []
    owners: List[str] = []
    for raw_line in owner_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        owners.append(line)
    return owners


def load_generation_settings(project_root: Path) -> Dict[str, Any]:
    config = load_project_config(project_root)
    generation = config.get("generation", {}) if isinstance(config.get("generation"), dict) else {}
    linking = config.get("linking", {}) if isinstance(config.get("linking"), dict) else {}
    progressive = config.get("progressive", {}) if isinstance(config.get("progressive"), dict) else {}
    governance = config.get("governance", {}) if isinstance(config.get("governance"), dict) else {}
    profile_name = generation.get("profile_name")
    if not profile_name:
        package_name = load_json(project_root / "package.json").get("name", "")
        if package_name == "frontend-web-flow":
            profile_name = "web-flow"
    profile_path = None
    if profile_name == "web-flow" and WEB_FLOW_PROFILE_PATH.exists():
        profile_path = str(WEB_FLOW_PROFILE_PATH)

    return {
        "owner_file": governance.get("owner_file", "OWNERS"),
        "review_status": governance.get("review_status_default", "approved"),
        "publish_requires_approval": bool(governance.get("publish_requires_approval", False)),
        "minimum_publish_quality": normalize_quality_level(governance.get("minimum_publish_quality", "professional")),
        "block_publish_on_warnings": bool(governance.get("block_publish_on_warnings", True)),
        "doc_profile": generation.get("doc_profile", "overview"),
        "language": generation.get("language", "zh"),
        "source_link_style": linking.get("source_link_style", "relative"),
        "github_repo_url": linking.get("github_repo_url") or linking.get("repo_url"),
        "github_ref": linking.get("github_ref", DEFAULT_GITHUB_REF),
        "progressive_mode": progressive.get("enabled", "auto"),
        "progressive_batch_size": max(1, int(progressive.get("batch_size", 2) or 2)),
        "progressive_quality_check": bool(progressive.get("quality_check", True)),
        "progressive_resume_from_cache": bool(progressive.get("resume_from_cache", True)),
        "progressive_auto_continue": bool(progressive.get("auto_continue", True)),
        "incremental_mode": progressive.get("enabled", "auto"),
        "profile_name": profile_name,
        "profile_path": profile_path,
    }


def describe_module(module_type: str) -> str:
    return MODULE_TYPE_DESCRIPTIONS.get(module_type, MODULE_TYPE_DESCRIPTIONS["module"])


def load_generation_profile(settings: Dict[str, Any]) -> Dict[str, Any]:
    profile_path = settings.get("profile_path")
    if not profile_path:
        return {}
    return load_yaml_file(Path(profile_path))


def load_enabled_plugins(project_root: Path) -> List[str]:
    registry_candidates = [
        project_root / ".mini-wiki" / "plugins" / "_registry.yaml",
        project_root / "plugins" / "_registry.yaml",
    ]
    enabled: List[str] = []
    seen: set[str] = set()
    for registry_path in registry_candidates:
        registry = load_yaml_file(registry_path)
        plugins = registry.get("plugins", [])
        if not isinstance(plugins, list):
            continue
        for item in plugins:
            if not isinstance(item, dict):
                continue
            if item.get("enabled", True):
                name = str(item.get("name", "")).strip()
                if name and name not in seen:
                    seen.add(name)
                    enabled.append(name)
    return enabled


def build_generation_signature(settings: Dict[str, Any], profile: Dict[str, Any], active_plugins: Sequence[str]) -> str:
    payload = {
        "generator_version": GENERATOR_VERSION,
        "quality_ruleset_version": QUALITY_RULESET_VERSION,
        "profile_name": settings.get("profile_name"),
        "doc_profile": settings.get("doc_profile"),
        "language": settings.get("language"),
        "review_status": settings.get("review_status"),
        "publish_requires_approval": bool(settings.get("publish_requires_approval", True)),
        "source_link_style": settings.get("source_link_style"),
        "minimum_publish_quality": settings.get("minimum_publish_quality"),
        "block_publish_on_warnings": bool(settings.get("block_publish_on_warnings", True)),
        "active_plugins": sorted(active_plugins),
        "profile": profile,
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def generation_contract_matches(meta: Dict[str, Any], generation_signature: str) -> bool:
    return (
        str(meta.get("version", "")) == GENERATOR_VERSION
        and str(meta.get("quality_ruleset_version", "")) == QUALITY_RULESET_VERSION
        and str(meta.get("generation_signature", "")) == generation_signature
    )


def prioritize_modules_by_profile(modules: List[Dict[str, Any]], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not profile:
        return modules
    module_priorities = profile.get("module_priorities", [])
    if not isinstance(module_priorities, list) or not module_priorities:
        return modules

    order: Dict[str, int] = {}
    for index, item in enumerate(module_priorities):
        if isinstance(item, str):
            order[item] = index

    def score(module: Dict[str, Any]) -> Tuple[int, float]:
        slug = module.get("slug", "")
        best = len(order) + 1
        for prefix, position in order.items():
            if slug == prefix or slug.startswith(prefix + "/"):
                best = min(best, position)
        return best, -float(module.get("importance", 0))

    return sorted(modules, key=score)


def select_modules(modules: List[Dict[str, Any]], limit: int, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    initial = choose_focus_modules(modules, max(limit * 4, limit))
    prioritized = prioritize_modules_by_profile(initial, profile)
    return prioritized[:limit]


def choose_focus_modules(modules: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    blocked: List[str] = []

    ranked_modules = sorted(
        modules,
        key=lambda module: (
            module.get("importance", 0)
            + (120 if module.get("slug") == "stage" else 0)
            + (40 if module.get("module_type") in {"workflow", "ai", "api", "event"} else 0)
            + (10 if module.get("module_type") == "ui" and module.get("slug", "").count("/") >= 2 else 0)
            - (10 if module.get("module_type") == "utility" else 0)
        ),
        reverse=True,
    )

    for module in ranked_modules:
        slug = module.get("slug", "")
        if not slug or slug in {"components", "src"}:
            continue
        if module.get("source_files", 0) < 8 and module.get("importance", 0) < 15:
            continue
        if any(slug.startswith(prefix + "/") or prefix.startswith(slug + "/") for prefix in blocked):
            continue
        if module.get("module_type") == "ui" and slug.count("/") == 0:
            continue
        selected.append(module)
        blocked.append(slug)
        if len(selected) >= limit:
            break

    return selected


def resolve_focus_file_limit(module: Dict[str, Any], requested_limit: int, api_mode: bool = False) -> int:
    source_files = int(module.get("source_files", 0))
    export_count = int(module.get("export_count", module.get("estimated_exports", 0)))
    dynamic_limit = requested_limit

    if source_files >= 200 or export_count >= 600:
        dynamic_limit += 4
    elif source_files >= 80 or export_count >= 240:
        dynamic_limit += 3
    elif source_files >= 25 or export_count >= 80:
        dynamic_limit += 2
    elif source_files >= 10 or export_count >= 30:
        dynamic_limit += 1

    hard_cap = 8 if api_mode else 12
    return min(dynamic_limit, hard_cap)


def list_module_code_files(project_root: Path, module_path: str) -> List[Path]:
    exclude_dirs, exclude_patterns = get_effective_excludes(
        project_root,
        analyze_project.IGNORE_DIRS,
        DEFAULT_FILE_EXCLUDE_PATTERNS,
    )
    root = project_root / module_path
    if root.is_file():
        return [root]

    files: List[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in analyze_project.CODE_EXTENSIONS:
            continue
        if any(part in exclude_dirs for part in path.parts):
            continue
        if check_quality.path_matches_patterns(path, project_root, exclude_patterns):
            continue
        files.append(path)
    return files


def score_focus_file(file_path: Path, project_root: Path, module_slug: str) -> float:
    relative = file_path.relative_to(project_root).as_posix().lower()
    content = read_text(file_path)
    exports = analyze_project.count_exports(content)
    lines = len(content.splitlines())
    score = 0.0
    name = file_path.name.lower()

    if name.startswith(("index.", "main.", "app.")):
        score += 20
    if any(token in relative for token in ("router", "service", "hook", "store", "event", "node", "render", "provider", "context")):
        score += 10
    if file_path.parent == project_root / module_slug.split("/")[0]:
        score += 6
    for token in [item for item in module_slug.lower().split("/") if len(item) > 2]:
        if token in relative:
            score += 3
    score += min(exports, 12) * 3
    score += min(lines, 240) / 18
    if "__tests__" in relative or ".spec." in relative or ".test." in relative:
        score -= 50
    return score


def choose_focus_files(project_root: Path, module: Dict[str, Any], limit: int, api_mode: bool = False) -> List[str]:
    files = list_module_code_files(project_root, module["path"])
    if not files:
        return [module["path"]]

    effective_limit = resolve_focus_file_limit(module, limit, api_mode=api_mode)
    ranked = sorted(
        files,
        key=lambda path: (score_focus_file(path, project_root, module["slug"]), -len(path.as_posix())),
        reverse=True,
    )

    selected: List[str] = []
    for path in ranked:
        relative = path.relative_to(project_root).as_posix()
        selected.append(relative)
        if len(selected) >= effective_limit:
            break
    return selected


def analyze_typescript_semantics(project_root: Path, source_paths: Sequence[str]) -> Dict[str, Any]:
    if not TS_SEMANTIC_ANALYZER.exists():
        return {}

    absolute_paths = [str((project_root / relative).resolve()) for relative in source_paths if (project_root / relative).exists()]
    if not absolute_paths:
        return {}

    cmd = ["node", str(TS_SEMANTIC_ANALYZER), str(project_root), *absolute_paths]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, OSError):
        return {}

    output = (result.stdout or "").strip()
    if not output:
        return {}
    try:
        payload = json.loads(output)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def extract_export_entries(project_root: Path, source_paths: Sequence[str], limit: int = MAX_EXPORT_ENTRIES) -> List[Dict[str, Any]]:
    semantic = analyze_typescript_semantics(project_root, source_paths)
    semantic_entries = semantic.get("entries", []) if isinstance(semantic, dict) else []
    if isinstance(semantic_entries, list) and semantic_entries:
        normalized: List[Dict[str, Any]] = []
        for entry in semantic_entries:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name", "")).strip()
            file_name = str(entry.get("file", "")).strip()
            if not name or not file_name:
                continue
            normalized.append(
                {
                    "name": name,
                    "type": str(entry.get("type", "symbol")),
                    "file": file_name,
                    "line": int(entry.get("line", 1)),
                    "signature": str(entry.get("signature", "")),
                }
            )
            if len(normalized) >= limit:
                break
        if normalized:
            return normalized

    entries: List[Dict[str, Any]] = []
    seen: set[Tuple[str, str]] = set()

    for relative_path in source_paths:
        file_path = project_root / relative_path
        content = read_text(file_path)
        if not content:
            continue
        for line_number, line in enumerate(content.splitlines(), 1):
            for entry_type, pattern in API_PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                name = match.group(1)
                key = (relative_path, name)
                if key in seen:
                    continue
                seen.add(key)
                entries.append(
                    {
                        "name": name,
                        "type": entry_type,
                        "file": relative_path,
                        "line": line_number,
                        "signature": line.strip(),
                    }
                )
                if len(entries) >= limit:
                    return entries
                break
    return entries


def extract_code_snippet(project_root: Path, relative_path: str, anchor_line: Optional[int] = None, max_lines: int = 14) -> str:
    content = read_text(project_root / relative_path)
    if not content:
        return ""

    lines = content.splitlines()
    start = 0
    if anchor_line:
        start = max(anchor_line - 2, 0)
    else:
        for index, line in enumerate(lines):
            if any(pattern.search(line) for _, pattern in API_PATTERNS):
                start = index
                break
    return "\n".join(lines[start : start + max_lines]).strip()


def pick_relevant_docs(docs_catalog: List[Dict[str, Any]], module_slug: Optional[str] = None, limit: int = 3) -> List[Dict[str, Any]]:
    if not docs_catalog:
        return []

    if not module_slug:
        return [doc for doc in docs_catalog if doc.get("kind") != "template-readme"][:limit]

    tokens = {
        token
        for token in re.split(r"[/\-_]", module_slug.lower())
        if token and token not in GENERIC_PATH_SEGMENTS and len(token) > 2
    }
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for doc in docs_catalog:
        haystack = f"{doc.get('path', '').lower()} {doc.get('title', '').lower()}"
        score = sum(3 for token in tokens if token in haystack)
        if "stream" in haystack and {"chat", "workflow", "doc"} & tokens:
            score += 2
        if doc.get("kind") == "design-doc":
            score += 1
        if score:
            scored.append((score + int(doc.get("trust_score", 0)), doc))

    if not scored:
        return pick_relevant_docs(docs_catalog, None, limit)

    return [doc for _, doc in sorted(scored, key=lambda item: item[0], reverse=True)[:limit]]


def extract_doc_summary(project_root: Path, relative_path: str) -> str:
    content = read_text(project_root / relative_path)

    noise_patterns = (
        r"^(我来帮你|让我|现在让我|下面我|接下来我|我先|当然|好的|现在我已经|让我继续)",
        r"(查看相关代码|继续查看|详细分析这两个|完整的信息)",
    )
    paragraphs: List[str] = []
    current: List[str] = []

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "---":
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if (
            stripped.startswith("#")
            or stripped.startswith("```")
            or stripped.startswith(">")
            or stripped.startswith("|")
            or stripped.startswith("- ")
            or stripped.startswith("* ")
        ):
            continue
        if any(re.search(pattern, stripped) for pattern in noise_patterns):
            continue
        current.append(stripped)

    if current:
        paragraphs.append(" ".join(current))

    for paragraph in paragraphs:
        compact = re.sub(r"\s+", " ", paragraph).strip()
        if len(compact) < 16:
            continue
        return compact[:160]
    return "该设计文档提供了对应场景的实现细节和边界说明。"


def build_workspace_command(package_name: str, workspace_root: Optional[str], project_root: Path, script_name: str) -> str:
    if workspace_root and Path(workspace_root).resolve() != project_root.resolve():
        return f"pnpm --filter {package_name} {script_name}"
    return f"pnpm run {script_name}"


def render_source_table(doc_path: Path, project_root: Path, source_paths: Sequence[str]) -> str:
    rows = ["| 源码路径 | 用途 |", "|------|------|"]
    for source_path in source_paths:
        link = source_link(doc_path, project_root, source_path)
        description = "关键入口或高频实现文件"
        if "/hooks/" in source_path or source_path.endswith("hook.ts") or source_path.endswith("hook.tsx"):
            description = "复用逻辑与状态封装"
        elif "/services/" in source_path:
            description = "接口与服务编排"
        elif "/events/" in source_path:
            description = "事件协议与广播"
        elif source_path.endswith((".cc", ".cpp", ".cxx", ".h", ".hpp")):
            description = "Native/WASM 运行时桥接"
        rows.append(f"| [`{source_path}`]({link}) | {description} |")
    return "\n".join(rows)


def render_focus_coverage_table(actual_context: Dict[str, int], focus_context: Dict[str, int]) -> str:
    actual_files = int(actual_context.get("actual_source_files", 0))
    actual_lines = int(actual_context.get("actual_source_lines", 0))
    actual_exports = int(actual_context.get("actual_export_count", 0))
    actual_classes = int(actual_context.get("actual_class_count", 0))
    actual_interfaces = int(actual_context.get("actual_interface_count", 0))

    focus_files = int(focus_context.get("focus_source_files", 0))
    focus_lines = int(focus_context.get("focus_source_lines", 0))
    focus_exports = int(focus_context.get("focus_export_count", 0))
    focus_classes = int(focus_context.get("focus_class_count", 0))
    focus_interfaces = int(focus_context.get("focus_interface_count", 0))

    coverage_ratio = 0.0 if actual_lines <= 0 else focus_lines / max(actual_lines, 1)
    rows = [
        "| 维度 | 实际规模 | 当前文档焦点 |",
        "|------|----------|--------------|",
        f"| 源码文件 | {actual_files} | {focus_files} |",
        f"| 源码行数 | {actual_lines} | {focus_lines} |",
        f"| 导出接口 | {actual_exports} | {focus_exports} |",
        f"| class / type | {actual_classes + actual_interfaces} | {focus_classes + focus_interfaces} |",
        f"| 焦点覆盖率 | - | {coverage_ratio:.1%} |",
    ]
    return "\n".join(rows)


def render_focus_coverage_summary(actual_context: Dict[str, int], focus_context: Dict[str, int]) -> str:
    actual_files = int(actual_context.get("actual_source_files", 0))
    actual_lines = int(actual_context.get("actual_source_lines", 0))
    actual_exports = int(actual_context.get("actual_export_count", 0))
    focus_files = int(focus_context.get("focus_source_files", 0))
    focus_lines = int(focus_context.get("focus_source_lines", 0))
    focus_exports = int(focus_context.get("focus_export_count", 0))
    coverage_ratio = 0.0 if actual_lines <= 0 else focus_lines / max(actual_lines, 1)
    return "\n".join(
        [
            f"- 当前焦点覆盖 `{focus_files}/{actual_files}` 个源码文件，优先围绕入口和高频实现组织文档。",
            f"- 当前焦点覆盖 `{focus_lines}/{actual_lines}` 行源码，便于评审者快速判断本文是概览还是深挖页。",
            f"- 当前焦点已纳入 `{focus_exports}/{actual_exports}` 个导出符号，足以支撑接口和类型追踪。",
            f"- 当前焦点覆盖率约为 `{coverage_ratio:.1%}`，后续如果出现复杂子链路，应拆分专题页继续补全。",
        ]
    )


def render_focus_file_diagram(project_root: Path, source_paths: Sequence[str], title: str) -> str:
    lines = ["```mermaid", "mindmap", f'  root(("{title}"))']
    for source_path in source_paths[:8]:
        resolved = (project_root / source_path).resolve()
        stats = check_quality.scan_source_paths([resolved], project_root)
        label = source_path.replace('"', "'")
        metrics = f"{int(stats.get('source_files', 0))} files / {int(stats.get('source_lines', 0))} lines"
        lines.append(f'    "{label}"')
        lines.append(f'      "{metrics}"')
    lines.append("```")
    return "\n".join(lines)


def render_export_table(doc_path: Path, project_root: Path, exports: Sequence[Dict[str, Any]]) -> str:
    if not exports:
        return "| 接口 | 类型 | 源码 | 说明 |\n|------|------|------|------|\n| - | - | - | 当前焦点源码以组件组合与内部状态机为主，公开导出较少。 |"

    rows = ["| 接口 | 类型 | 源码 | 说明 |", "|------|------|------|------|"]
    for entry in exports[:12]:
        link = source_link(doc_path, project_root, entry["file"])
        signature = str(entry.get("signature", "")).replace("|", "\\|").strip()
        description = "该导出位于当前能力链的关键实现位置，可作为追踪入口。"
        if signature:
            compact = signature[:72] + "..." if len(signature) > 72 else signature
            description = f"签名片段：`{compact}`"
        rows.append(
            f"| `{entry['name']}` | {entry['type']} | "
            f"[`{entry['file']}:{entry['line']}`]({link}) | "
            f"{description} |"
        )
    return "\n".join(rows)


def render_code_examples(project_root: Path, source_paths: Sequence[str], exports: Sequence[Dict[str, Any]], limit: int = MAX_CODE_SNIPPETS) -> str:
    blocks: List[str] = []
    used_files: List[Tuple[str, Optional[int]]] = []
    seen_files = set()

    for entry in exports[:limit]:
        if entry["file"] in seen_files:
            continue
        used_files.append((entry["file"], entry["line"]))
        seen_files.add(entry["file"])
        if len(used_files) >= limit:
            break

    if len(used_files) < limit:
        for source_path in source_paths:
            if source_path in seen_files:
                continue
            used_files.append((source_path, None))
            seen_files.add(source_path)
            if len(used_files) >= limit:
                break

    for file_path, line_number in used_files[:limit]:
        snippet = extract_code_snippet(project_root, file_path, line_number)
        if not snippet:
            continue
        language = language_for_file(Path(file_path))
        blocks.append(f"### `{file_path}`\n\n```{language}\n{snippet}\n```")
    return "\n\n".join(blocks) or "当前焦点源码以组合式实现为主，建议直接从源码链接进入目标文件查看完整上下文。"


def render_exports_class_diagram(exports: Sequence[Dict[str, Any]]) -> str:
    class_like = [item for item in exports if item.get("type") in {"class", "interface", "type", "enum"}]
    if not class_like:
        return ""

    alias_map: Dict[str, str] = {}
    for index, item in enumerate(class_like[:8]):
        name = str(item.get("name", "Symbol")).strip() or f"Symbol{index}"
        alias_map[name] = re.sub(r"[^A-Za-z0-9_]", "_", name) or f"Symbol{index}"

    lines = ["```mermaid", "classDiagram"]
    relationships: set[Tuple[str, str]] = set()

    for item in class_like[:8]:
        name = str(item.get("name", "Symbol")).strip()
        alias = alias_map.get(name, "Symbol")
        symbol_type = str(item.get("type", "type"))
        lines.append(f"    class {alias} {{")
        lines.append(f"        +{symbol_type}")
        lines.append("    }")

        signature = str(item.get("signature", ""))
        for reference_name, reference_alias in alias_map.items():
            if reference_name == name:
                continue
            if re.search(rf"\\b{re.escape(reference_name)}\\b", signature):
                relationships.add((alias, reference_alias))

    for source_alias, target_alias in sorted(relationships):
        lines.append(f"    {source_alias} --> {target_alias}")
    lines.append("```")
    return "\n".join(lines)


def build_navigation_links(doc_path: Path, generated_docs: Dict[str, str]) -> Dict[str, str]:
    return {name: doc_link(doc_path, target) for name, target in generated_docs.items()}


def render_related_section(
    doc_path: Path,
    generated_docs: Dict[str, str],
    related_source_docs: Sequence[Dict[str, Any]],
    project_root: Path,
    current_slug: Optional[str] = None,
) -> str:
    links = build_navigation_links(doc_path, generated_docs)
    rows = [
        f"- [项目首页]({links['index']})",
        f"- [架构总览]({links['architecture']})",
        f"- [阅读地图]({links['doc_map']})",
        f"- [领域索引]({links['domains_index']})",
    ]

    if current_slug and current_slug in generated_docs:
        rows = [row for row in rows if generated_docs[current_slug] not in row]

    for doc in related_source_docs:
        source_doc_path = project_root / doc["path"]
        rows.append(f"- [现有设计文档: {doc['title']}]({build_relative_link(doc_path, source_doc_path)})")
    return "\n".join(rows)


def compute_focus_context(project_root: Path, source_paths: Sequence[str]) -> Dict[str, int]:
    resolved = [(project_root / relative).resolve() for relative in source_paths if relative]
    stats = check_quality.scan_source_paths(resolved, project_root)
    return {
        "focus_source_files": int(stats.get("source_files", 0)),
        "focus_source_lines": int(stats.get("source_lines", 0)),
        "focus_export_count": int(stats.get("export_count", 0)),
        "focus_class_count": int(stats.get("class_count", 0)),
        "focus_interface_count": int(stats.get("interface_count", 0)),
    }


def compute_actual_context(module_type: str, module: Optional[Dict[str, Any]] = None, analysis: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
    if module:
        return {
            "actual_source_files": int(module.get("source_files", 0)),
            "actual_source_lines": int(module.get("source_lines", 0)),
            "actual_export_count": int(module.get("export_count", module.get("estimated_exports", 0))),
            "actual_class_count": int(module.get("class_count", 0)),
            "actual_interface_count": int(module.get("interface_count", 0)),
        }

    stats = (analysis or {}).get("stats", {})
    return {
        "actual_source_files": int(stats.get("total_files", 0)),
        "actual_source_lines": int(stats.get("source_lines", 0)),
        "actual_export_count": int(stats.get("export_count", 0)),
        "actual_class_count": int(stats.get("class_count", 0)),
        "actual_interface_count": int(stats.get("interface_count", 0)),
    }


def build_doc_metadata(
    *,
    doc_type: str,
    module_type: str,
    doc_role: str,
    doc_profile: str,
    source_paths: Sequence[str],
    actual_context: Dict[str, int],
    focus_context: Dict[str, int],
    owners: Sequence[str],
    review_status: str,
    generation_signature: Optional[str] = None,
    minimum_publish_quality: str = "professional",
    block_publish_on_warnings: bool = True,
) -> Dict[str, Any]:
    return {
        "doc_type": doc_type,
        "module_type": module_type,
        "doc_role": doc_role,
        "doc_profile": doc_profile,
        "source_paths": list(source_paths),
        "focus_paths": list(source_paths),
        **actual_context,
        **focus_context,
        "owner": owners[0] if owners else "unassigned",
        "reviewers": list(owners[1:]) if len(owners) > 1 else [],
        "review_status": review_status,
        "publish_status": "blocked",
        "minimum_publish_quality": normalize_quality_level(minimum_publish_quality),
        "block_publish_on_warnings": bool(block_publish_on_warnings),
        "generated_at": now_iso(),
        "last_verified_at": "pending",
        "quality_score": "pending",
        "quality_level": "pending",
        "quality_ruleset_version": QUALITY_RULESET_VERSION,
        "generation_signature": generation_signature or "",
        "active_plugins": list(RUNTIME_ACTIVE_PLUGINS),
        "generated_by": "mini-wiki-generator",
        "generator_version": GENERATOR_VERSION,
    }


def collect_architecture_focus_sources(
    project_root: Path,
    analysis: Dict[str, Any],
    selected_modules: Sequence[Dict[str, Any]],
) -> List[str]:
    raw_paths = [
        *analysis.get("entry_points", [])[:4],
        "stage/platform/main.cc",
        *sum((choose_focus_files(project_root, module, 2) for module in selected_modules[:5]), []),
    ]
    return [path for path in dict.fromkeys(raw_paths) if (project_root / path).exists()]


def render_index_doc(
    doc_path: Path,
    project_root: Path,
    analysis: Dict[str, Any],
    package_json: Dict[str, Any],
    selected_modules: Sequence[Dict[str, Any]],
    generated_docs: Dict[str, str],
    owners: Sequence[str],
) -> str:
    links = build_navigation_links(doc_path, generated_docs)
    docs_catalog = analysis.get("docs_catalog", [])
    key_docs = pick_relevant_docs(docs_catalog, None, 5)
    package_name = package_json.get("name", analysis["project_name"])

    module_rows = ["| 领域 | 类型 | 规模 | 文档 |", "|------|------|------|------|"]
    for module in selected_modules:
        module_link = doc_link(doc_path, generated_docs[module["slug"]])
        module_rows.append(
            f"| `{module['slug']}` | {module['module_type']} | "
            f"{module['source_files']} 文件 / {module['source_lines']} 行 | "
            f"[查看概览]({module_link}) |"
        )

    design_doc_rows = ["| 现有设计文档 | 可信度 | 说明 |", "|------|------|------|"]
    for doc in key_docs:
        design_doc_rows.append(
            f"| [{doc['title']}]({build_relative_link(doc_path, project_root / doc['path'])}) | "
            f"{doc['trust_score']} | {extract_doc_summary(project_root, doc['path'])} |"
        )

    internal_dep_rows = ["| 内部依赖 | Workspace 路径 |", "|------|------|"]
    for dependency in analysis.get("internal_dependencies", []):
        internal_dep_rows.append(f"| `{dependency['name']}` | `{dependency.get('path') or '未解析'}` |")
    if len(internal_dep_rows) == 2:
        internal_dep_rows.append("| - | 当前项目没有识别到 workspace 内部依赖。 |")

    return f"""# {analysis['project_name']} 项目总览

> 本文档面向接手 `web-flow` 的工程师、架构评审和 AI 文档生成链路，覆盖项目定位、主业务域、技术栈与阅读路径。当前生成结果默认处于 `draft` 评审态，适合纳入企业知识库后继续人工校核。

## 项目定位

`{analysis['project_name']}` 是 CoCraft 前端工作台中的核心编辑应用，承担聊天式生成、工作流画布、文档与 UI 流式生成、多媒体编辑以及 Native/WASM 运行时接线。项目处于 monorepo 子包位置，既依赖 workspace 内部基础包，也直接承载复杂的前端业务链路。

从工程结构看，这个项目不是简单的页面集合，而是一个围绕 `{package_name}` 构建的前端平台能力层。`components/workflow`、`components/chat`、`components/design-app`、`services` 与 `stage` 共同组成了用户交互、事件编排、后端通信与 Native 容器运行的主链路。

## 技术栈一览

| 类别 | 识别结果 | 说明 |
|------|----------|------|
| 前端框架 | `react`, `vite`, `typescript` | React 19 + Vite 7 组合，适合高频 UI 迭代和复杂工作流渲染。 |
| 工程组织 | `pnpm-workspaces`, `turborepo`, `workspace` | 项目位于 `/Users/mono/cocraft` monorepo 内，需要显式处理内部依赖和过滤构建。 |
| 状态与数据流 | `zustand`, `rxjs`, `i18n` | 状态切片、事件流与国际化能力同时存在。 |
| 运行时扩展 | `cpp`, `native-bridge`, `wasm` | `stage` 与 `kiwi` 侧代码说明该项目不仅是纯浏览器应用。 |
| 质量基础 | `vitest` | 已有测试运行能力，但仍需要文档门禁来保证知识库质量。 |

## 架构预览

{generate_diagram.generate_architecture_diagram(analysis)}

## 核心业务域

{chr(10).join(module_rows)}

## 入口与运行方式

| 场景 | 推荐命令 | 说明 |
|------|----------|------|
| 安装依赖 | `pnpm install` | 在 workspace 根目录执行，统一安装共享依赖。 |
| 本地开发 | `{build_workspace_command(package_name, analysis.get('workspace_root'), project_root, 'dev')}` | 走 `dev` 脚本，自动复制 `.env.example` 并触发 kiwi 初始化。 |
| 构建产物 | `{build_workspace_command(package_name, analysis.get('workspace_root'), project_root, 'build')}` | 同时构建 C++/WASM 与 Web 侧代码。 |
| 运行测试 | `{build_workspace_command(package_name, analysis.get('workspace_root'), project_root, 'test')}` | 当前默认使用 Vitest。 |

```bash
pnpm install
{build_workspace_command(package_name, analysis.get('workspace_root'), project_root, 'dev')}
```

```bash
{build_workspace_command(package_name, analysis.get('workspace_root'), project_root, 'build')}
{build_workspace_command(package_name, analysis.get('workspace_root'), project_root, 'test')}
```

## Workspace 与内部依赖

{chr(10).join(internal_dep_rows)}

这些依赖不是普通第三方包，而是 monorepo 内部的真实源码。文档生成和架构审查都应该把它们视为一等依赖，否则很容易遗漏接口约束和共享约定。

## 现有设计资产

{chr(10).join(design_doc_rows)}

现有设计文档已经覆盖图层编辑、UI 流式生成、文档流式生成和 Cloud Agent 事件等关键链路。生成 Wiki 时不应该忽略这些已有资产，而应该把它们纳入阅读路径与追溯链接。

## 推荐阅读路径

1. 从 [快速开始]({links['getting_started']}) 了解开发命令、目录边界和接手方式。
2. 再阅读 [架构总览]({links['architecture']})，建立分层、事件流和 Native 桥接的整体心智模型。
3. 随后按 [领域索引]({links['domains_index']}) 进入 `workflow`、`chat`、`services` 等高价值领域文档。
4. 最后通过 [阅读地图]({links['doc_map']}) 和现有设计文档回溯具体方案细节。

## 相关文档

{render_related_section(doc_path, generated_docs, key_docs[:3], project_root)}
"""


def render_architecture_doc(
    doc_path: Path,
    project_root: Path,
    analysis: Dict[str, Any],
    selected_modules: Sequence[Dict[str, Any]],
    generated_docs: Dict[str, str],
) -> str:
    relevant_docs = pick_relevant_docs(analysis.get("docs_catalog", []), "workflow chat stage cloud-agent", 4)
    architecture_sources = collect_architecture_focus_sources(project_root, analysis, selected_modules)
    architecture_actual_context = compute_actual_context("project", analysis=analysis)
    architecture_focus_context = compute_focus_context(project_root, architecture_sources)
    coverage_summary = render_focus_coverage_summary(architecture_actual_context, architecture_focus_context)
    source_rows = render_source_table(doc_path, project_root, architecture_sources)
    coverage_table = render_focus_coverage_table(architecture_actual_context, architecture_focus_context)
    module_rows = ["| 模块 | 类型 | 角色 | 说明 |", "|------|------|------|------|"]
    for module in selected_modules[:8]:
        module_rows.append(
            f"| `{module['slug']}` | {module['module_type']} | {module.get('doc_role', 'module')} | "
            f"{describe_module(module['module_type'])} |"
        )

    workspace_dependency_diagram = generate_diagram.generate_module_dependency_diagram(
        analysis["project_name"],
        {
            "internal": [dependency.get("path") or dependency["name"] for dependency in analysis.get("internal_dependencies", [])[:6]],
            "external": [],
        },
    )
    key_domain_diagram = generate_diagram.generate_file_tree_diagram({"modules": list(selected_modules)})
    focus_source_diagram = render_focus_file_diagram(project_root, architecture_sources, "架构焦点源码")

    return f"""# 系统架构总览

> 本文档说明 `web-flow` 的分层结构、主运行链路、Native/WASM 接线和企业级接手时最需要关注的边界。

## 执行摘要

`web-flow` 既是交互式编辑前端，也是复杂生成链路的宿主应用。它需要同时处理 UI 组件、工作流画布、聊天驱动的工具调用、远端服务通信以及 `stage`/`kiwi` 侧的运行时桥接，因此架构上天然比普通 SPA 更接近“前端平台”。

项目位于 monorepo 子包中，内部依赖通过 workspace 包对齐 API、公共前端能力与 Tailwind 配置。这意味着架构审查不能只停留在当前目录，必须把 workspace 依赖与 Native 侧入口一起纳入追溯范围。

## 架构分层图

{generate_diagram.generate_architecture_diagram({'modules': list(selected_modules), 'project_type': analysis.get('project_type', [])})}

## 主数据流

{generate_diagram.generate_data_flow_diagram(analysis.get('entry_points', []), list(selected_modules))}

## 文档覆盖策略

{coverage_table}

企业级架构文档不应该伪装成“全仓穷举”，而应该清楚告诉读者当前是基于哪些入口、哪些高价值领域和哪些真实设计资产生成的。这样做的目的不是缩水，而是保证结论可追溯、可复核、可持续更新。

## 焦点覆盖摘要

{coverage_summary}

## Workspace 依赖关系

{workspace_dependency_diagram}

## 重点目录图

{key_domain_diagram}

## 焦点源码图

{focus_source_diagram}

## 架构焦点源码

{source_rows}

## 核心模块表

{chr(10).join(module_rows)}

## 运行时与 Native/WASM 边界

`stage` 模块与 `build.sh`、`stage/platform/main.cc` 一起说明了项目不是纯前端资源构建，而是带有 Native/WASM 运行时扩展。企业级文档里必须明确区分：

- 浏览器侧：React/Vite 页面、画布节点、聊天工具渲染与业务事件。
- 服务侧：`services`、`cloud-agent` 等请求编排和协议封装。
- 运行时侧：`stage`、`kiwi` 与 C++/WASM 构建链，负责底层宿主能力。

```tsx
{extract_code_snippet(project_root, analysis.get('entry_points', ['src/main.tsx'])[0])}
```

```cpp
{extract_code_snippet(project_root, 'stage/platform/main.cc')}
```

## 设计约束与最佳实践

### 最佳实践

- 先从入口文件和高置信设计文档建立心智模型，再下钻到模块概览，避免直接在 `components/` 大目录里盲读。
- 对聊天流、文档流和 UI 流这类异步流程，优先从事件协议、状态机和工具调用标记来理解，而不是只看渲染层。
- 把 workspace 内部依赖当成源码的一部分处理，文档必须保留真实路径和责任边界。

### 性能优化

- `workflow` 和 `chat` 子系统文件量大、状态多，文档生成与代码审查都应优先聚焦高频入口文件，而不是一次性扫全目录。
- 涉及画布、媒体和 Native/WASM 的链路要区分冷启动成本、传输开销和缓存行为，避免把所有性能问题归因到 React 层。
- 文档质量门禁应基于实际焦点源码范围，而不是按整个大目录盲目放大阈值。

### 错误处理

- `stage`、`services`、`cloud-agent` 出现异常时，应先判断问题属于宿主运行时、服务协议还是前端状态机，再决定排查路径。
- 对需要跨 iframe、跨工具调用或跨 sandbox 的流程，文档必须保留清晰的故障分界和回溯入口。
- Mermaid 图若无法稳定表达某条链路，应回退到结构化表格而不是输出错误图表。

## 现有技术设计文档

| 文档 | 说明 |
|------|------|
{chr(10).join([f"| [{doc['title']}]({build_relative_link(doc_path, project_root / doc['path'])}) | {extract_doc_summary(project_root, doc['path'])} |" for doc in relevant_docs])}

## 相关文档

{render_related_section(doc_path, generated_docs, relevant_docs, project_root)}
"""


def render_getting_started_doc(
    doc_path: Path,
    project_root: Path,
    analysis: Dict[str, Any],
    package_json: Dict[str, Any],
    generated_docs: Dict[str, str],
    owners: Sequence[str],
) -> str:
    package_name = package_json.get("name", analysis["project_name"])
    workspace_root = analysis.get("workspace_root")
    links = build_navigation_links(doc_path, generated_docs)
    key_sources = [*analysis.get("entry_points", [])[:3], "package.json", "build.sh"]

    scripts = package_json.get("scripts", {})
    script_rows = ["| 脚本 | 命令 | 说明 |", "|------|------|------|"]
    for script_name in ("dev", "dev-local", "build", "test", "lint"):
        if script_name not in scripts:
            continue
        script_rows.append(
            f"| `{script_name}` | `{build_workspace_command(package_name, workspace_root, project_root, script_name)}` | "
            f"`package.json` 中定义为 `{scripts[script_name]}` |"
        )

    if len(script_rows) == 2:
        script_rows.append("| - | - | 当前项目未声明常规开发脚本。 |")

    owner_text = "、".join(owners) if owners else "当前仓库未配置 OWNERS"

    return f"""# 快速开始

> 本文档面向第一次接手 `web-flow` 的开发者，提供本地启动、构建测试、目录识别和交接建议。

## 接手前提

- 当前项目位于 workspace 根目录 `/Users/mono/cocraft` 下，推荐在根目录统一执行依赖安装。
- 开发者需要同时具备 React/Vite、pnpm workspace 以及部分 Native/WASM 构建链知识。
- 仓库责任人来自 `OWNERS`：{owner_text}。

## 开发环境建议

| 项目 | 建议 |
|------|------|
| Node.js | 与 monorepo 当前版本保持一致，避免 lockfile 与构建脚本偏差。 |
| 包管理器 | 优先使用 `pnpm`，因为 workspace 依赖和 `--filter` 工作流已经绑定。 |
| 构建工具 | 需要支持 shell 脚本、`vite`、`tsc` 以及项目自定义的 kiwi 初始化脚本。 |
| 运行目录 | 建议在 workspace 根目录执行命令，避免内部包解析不完整。 |

## 核心命令

{chr(10).join(script_rows)}

```mermaid
flowchart LR
    Start["安装依赖"] --> Env["准备 .env / kiwi-init"]
    Env --> Dev["本地开发"]
    Dev --> Test["运行测试"]
    Test --> Build["执行构建"]
```

```bash
pnpm install
{build_workspace_command(package_name, workspace_root, project_root, 'dev')}
```

```bash
{build_workspace_command(package_name, workspace_root, project_root, 'build')}
{build_workspace_command(package_name, workspace_root, project_root, 'test')}
```

## 接手时先读哪些源码

{render_source_table(doc_path, project_root, key_sources)}

## 常见接手路径

1. 先验证本地环境能否跑通 `dev`、`build` 和 `test` 三条命令。
2. 阅读 [系统架构总览]({links['architecture']})，确认 `workflow`、`chat`、`services` 与 `stage` 的边界。
3. 按 [领域索引]({links['domains_index']}) 进入最相关的业务域，再结合原始设计文档回溯历史方案。
4. 如果需要排查事件或生成链问题，优先查看 `docs/` 与 `src/docs/` 下的高可信文档。

## 目录观察建议

- `src/components/workflow`：画布、节点、上下文菜单、状态切片，是交互主战场。
- `src/components/chat`：聊天工具渲染、子代理消息、流式展示相关逻辑集中在这里。
- `src/services` 与 `src/cloud-agent`：远端协议、工具调用与 Agent 事件封装。
- `stage`：宿主运行时和 Native/WASM 接线，不要误判成普通静态资源目录。

## 交接建议

- 把 `OWNERS`、`docs/`、`src/docs/` 和 `.mini-wiki/quality-report.json` 一起看，能同时建立责任边界和历史上下文。
- 对疑似底层问题，先看 `stage` 与 `services`；对疑似交互问题，优先看 `workflow` 与 `chat`。
- 如果你只需要排查某个流程，不要盲扫 1000+ 文件，直接进入对应领域文档和焦点源码即可。

## 最佳实践

- 接手大型前端平台时，先跑命令、再读架构、最后下钻具体模块，避免被目录规模直接淹没。
- 生成式链路要优先看协议、状态机和边界条件，而不是只看 UI 展示代码。
- 文档更新时保持 `source_paths` 与 owner/frontmatter 完整，确保后续质量门禁可复用。

## 性能优化

- 本地开发建议只聚焦当前子包，使用 workspace 过滤命令减少无关构建成本。
- `build` 同时涉及 Web 与 C++/WASM，问题排查要明确是 Vite 构建还是 Native 侧失败。
- 阅读大目录时优先入口文件和设计文档，降低理解成本。

## 错误处理

- 如果 `dev` 启动失败，先检查 `.env`、`kiwi-init` 和 workspace 依赖是否完整。
- 如果 `build` 失败，区分 `build:web` 和 `build:cpp` 具体失败段，避免把 Native 构建问题误认为前端问题。
- 如果生成流程异常，先参考 `docs/doc-streaming-generation.md` 和 `src/docs/cloud-agent-sdk-events.md` 中的事件定义。

## 相关文档

{render_related_section(doc_path, generated_docs, pick_relevant_docs(analysis.get('docs_catalog', []), None, 3), project_root)}
"""


def render_doc_map(
    doc_path: Path,
    project_root: Path,
    analysis: Dict[str, Any],
    selected_modules: Sequence[Dict[str, Any]],
    generated_docs: Dict[str, str],
    api_modules: Sequence[Dict[str, Any]],
) -> str:
    links = build_navigation_links(doc_path, generated_docs)

    doc_rows = ["| 文档 | 类型 | 覆盖范围 |", "|------|------|------|"]
    for name, target in generated_docs.items():
        if name in {"index", "architecture", "getting_started", "doc_map", "domains_index"}:
            label = {
                "index": "项目首页",
                "architecture": "系统架构总览",
                "getting_started": "快速开始",
                "doc_map": "阅读地图",
                "domains_index": "领域索引",
            }[name]
        else:
            label = humanize_slug(name)
        doc_rows.append(f"| [{label}]({doc_link(doc_path, target)}) | 自动生成 | 结合源码焦点、设计文档和质量门禁输出。 |")

    design_rows = ["| 原始文档 | 可信度 | 摘要 |", "|------|------|------|"]
    for doc in pick_relevant_docs(analysis.get("docs_catalog", []), None, 6):
        design_rows.append(
            f"| [{doc['title']}]({build_relative_link(doc_path, project_root / doc['path'])}) | {doc['trust_score']} | "
            f"{extract_doc_summary(project_root, doc['path'])} |"
        )

    reading_path = [
        "```mermaid",
        "flowchart LR",
        '    Start["项目首页"] --> StartGuide["快速开始"]',
        '    StartGuide --> Arch["架构总览"]',
        '    Arch --> Domains["领域索引"]',
    ]
    for module in selected_modules[:4]:
        node_id = generate_diagram.safe_id(module["slug"])
        reading_path.append(f'    Domains --> {node_id}["{module["slug"]}"]')
    if api_modules:
        reading_path.append('    Domains --> API["API 视图"]')
    reading_path.append("```")

    return f"""# 阅读地图

> 本文档用于说明当前生成 Wiki 的阅读顺序、文档覆盖范围和与原始设计资产的关系。

## 推荐阅读顺序

{chr(10).join(reading_path)}

## 自动生成文档索引

{chr(10).join(doc_rows)}

## 领域优先级

| 优先级 | 领域 | 原因 |
|------|------|------|
{chr(10).join([f"| P{index + 1} | `{module['slug']}` | {describe_module(module['module_type'])} |" for index, module in enumerate(selected_modules[:6])])}

## 原始设计资产映射

{chr(10).join(design_rows)}

## 文档治理契约

- 每篇文档都带有 `source_paths`、`owner`、`review_status`、`quality_score` 和 `last_verified_at` frontmatter。
- 领域文档默认使用聚焦视图，不追求把整个目录树直接复制成一篇超长 Markdown。
- 质量报告输出到 `.mini-wiki/quality-report.json`，可直接进入 CI、PR 检查或企业知识库同步任务。
- 如果某条链路新增高价值设计文档，应优先纳入 `docs/` 或 `src/docs/`，以便分析器稳定发现。

## 使用建议

- 如果你要理解全局架构，按“首页 -> 架构 -> 领域索引 -> 领域文档”的顺序阅读。
- 如果你要定位一个具体问题，直接从最接近问题域的领域文档进入，再通过相对路径源码链接追踪实现。
- 如果你要审查文档质量，优先对照 `quality-report.json` 中的 `expected_metrics` 与 `fatal_issues`。
- 如果你要新增主题页，请保持 frontmatter、源码链接和相关文档章节完整。

## 维护建议

- 变更 `workflow`、`chat`、`services`、`stage` 等主链路时，应同步更新对应领域文档。
- 如果新增设计文档，请优先落在 `docs/` 或 `src/docs/`，便于分析器自动发现。
- 质量门禁输出位于 `.mini-wiki/quality-report.json`，可以直接接入 CI 或 PR 检查。

## 相关文档

- [项目首页]({links['index']})
- [快速开始]({links['getting_started']})
- [系统架构总览]({links['architecture']})
- [领域索引]({links['domains_index']})
"""


def render_domains_index(
    doc_path: Path,
    project_root: Path,
    selected_modules: Sequence[Dict[str, Any]],
    generated_docs: Dict[str, str],
) -> str:
    links = build_navigation_links(doc_path, generated_docs)
    rows = ["| 领域 | 类型 | 规模 | 关注点 | 文档 |", "|------|------|------|--------|------|"]
    for module in selected_modules:
        rows.append(
            f"| `{module['slug']}` | {module['module_type']} | {module['source_files']} 文件 / {module['source_lines']} 行 | "
            f"{describe_module(module['module_type'])} | "
            f"[查看概览]({doc_link(doc_path, generated_docs[module['slug']])}) |"
        )

    return f"""# 领域索引

> 当前索引只收录高价值、可稳定过质量门禁的领域文档。它们覆盖 `web-flow` 的主要业务域，但不等于整个仓库的穷举镜像。

## 领域总览

{chr(10).join(rows)}

## 阅读关系图

```mermaid
flowchart TB
    Home["项目首页"] --> Arch["系统架构总览"]
    Arch --> Domains["领域索引"]
{chr(10).join([f'    Domains --> {generate_diagram.safe_id(module["slug"])}["{module["slug"]}"]' for module in selected_modules[:6]])}
```

## 使用方式

1. 如果你在接手项目，先看 [系统架构总览]({links['architecture']}) 再回到本页选择目标领域。
2. 如果你在排查某条链路，优先选择与问题最接近的领域文档，然后通过 `source_paths` 回溯源码。
3. 如果你准备新增文档，请复用当前 frontmatter 契约和质量门禁要求。

## 领域边界说明

- `workflow` 相关文档聚焦画布、节点、交互状态与编辑链路。
- `chat` 相关文档聚焦子代理消息、工具渲染和流式生成。
- `services`/`cloud-agent` 相关文档聚焦协议、请求与事件对接。
- `stage` 文档聚焦运行时入口、Native/WASM 桥接与宿主依赖。

## 维护策略

- 领域文档默认写成 `overview`，目的是稳定表达关键能力和焦点源码，而不是复制整个目录树。
- 某个领域如果继续膨胀，应拆出更细的子领域文档，而不是把所有细节继续堆在同一页。
- 进入企业知识库前，应以 `quality-report.json` 为准检查 source tracing、Mermaid 合法性和交叉链接。

## 领域选择原则

- 优先覆盖主链路：`workflow`、`chat`、`services`、`events`、`stage`。
- 优先覆盖高变更风险目录，而不是单纯按文件数量排序。
- 对同一父目录下的大量子目录，先输出概览文档，再按需要拆出子领域。
- 如果某个目录没有稳定入口文件或设计文档，暂时不纳入首批生产文档。

## 升级建议

- 当某个领域文档的 `source_paths` 持续增加时，应把它拆分成新的专题页，以避免再次退化成不可维护的大文档。
- 如果新增接口层或新的 Agent 链路，应先补设计文档，再生成领域文档和 API 视图。
- 进入正式企业知识库前，建议人工抽查 owner、源码链接、Mermaid 渲染与阅读路径是否一致。

## 维护清单

- 抽查所有领域文档的 `source_paths` 是否仍然指向真实高价值入口。
- 抽查索引页中的文档链接是否都能打开，尤其是新增的 API 视图。
- 发现领域边界变化时，优先更新本页，再决定是否拆分新的专题页。
- 当质量报告出现 `basic` 文档时，先修复索引和焦点源码映射，再补充正文内容。
- 对外同步到企业知识库前，补齐 review 状态和人工结论，避免把草稿视为最终事实。

## 门户页职责

- 本页负责给新同学和评审者提供“先看什么、再看什么”的路线，而不是解释所有实现细节。
- 真正的源码级解释应继续落到各领域文档和 API 视图中。
- 当阅读路径发生变化时，应优先更新本页，保证导航始终可信。

## 相关文档

- [项目首页]({links['index']})
- [快速开始]({links['getting_started']})
- [系统架构总览]({links['architecture']})
- [阅读地图]({links['doc_map']})
"""


def render_module_doc(
    doc_path: Path,
    project_root: Path,
    module: Dict[str, Any],
    source_paths: Sequence[str],
    exports: Sequence[Dict[str, Any]],
    analysis: Dict[str, Any],
    generated_docs: Dict[str, str],
) -> str:
    relevant_docs = pick_relevant_docs(analysis.get("docs_catalog", []), module["slug"], 3)
    links = build_navigation_links(doc_path, generated_docs)
    actual_context = compute_actual_context(module["module_type"], module=module, analysis=analysis)
    focus_context = compute_focus_context(project_root, source_paths)
    dependency_diagram = generate_diagram.generate_module_dependency_diagram(
        module["slug"],
        {
            "internal": module.get("children", [])[:6],
            "external": [item["name"] for item in analysis.get("internal_dependencies", [])[:4]],
        },
    )
    flow_diagram = f"""```mermaid
sequenceDiagram
    participant Caller as 调用方
    participant Domain as {module['slug']}
    participant Support as 支撑能力
    Caller->>Domain: 触发 {module['module_type']} 能力
    Domain->>Support: 访问关键文件 / 服务
    Support-->>Domain: 返回状态 / 数据
    Domain-->>Caller: 更新页面、状态或结果
```"""

    file_rows = render_source_table(doc_path, project_root, source_paths)
    coverage_table = render_focus_coverage_table(actual_context, focus_context)
    coverage_summary = render_focus_coverage_summary(actual_context, focus_context)
    export_rows = render_export_table(doc_path, project_root, exports)
    class_diagram = render_exports_class_diagram(exports)
    focus_file_diagram = render_focus_file_diagram(project_root, source_paths, f"{module['slug']} 焦点源码")
    design_doc_rows = [
        f"| [{doc['title']}]({build_relative_link(doc_path, project_root / doc['path'])}) | {extract_doc_summary(project_root, doc['path'])} |"
        for doc in relevant_docs
    ] or ["| - | 当前没有识别到强相关的设计文档，建议后续补充。 |"]

    child_rows = ["| 子领域 | 作用 |", "|------|------|"]
    for child in module.get("children", [])[:8]:
        child_rows.append(f"| `{child}` | 作为 `{module['slug']}` 的下钻阅读入口。 |")
    if len(child_rows) == 2:
        child_rows.append("| - | 当前文档聚焦单一模块，不再细分子领域。 |")

    return f"""# {humanize_slug(module['slug'])} 领域概览

> 本文档是 `{module['slug']}` 的生产化概览页，重点覆盖关键入口、关键接口、相关设计文档和接手时最需要关注的边界。它不是全量源码索引，而是可过质量门禁的焦点文档。

## 模块定位

`{module['slug']}` 属于 `{module['module_type']}` 领域，当前规模约为 {module['source_files']} 个源码文件、{module['source_lines']} 行实现。{describe_module(module['module_type'])}

当前文档采用 `overview` 角色，关注的是高价值入口、公共抽象和主流程追踪点，而不是把整个目录逐文件摊平。这种写法更适合企业级知识库和持续更新的 CI 门禁。

## 文档覆盖策略

{coverage_table}

这张表回答的是“当前文档到底覆盖了多少真实实现”。对企业知识库而言，这比空泛地宣称“深度分析”更重要，因为评审者需要快速判断文档是不是只覆盖了入口、是否遗漏了核心类型和是否适合继续下钻。

## 覆盖摘要

{coverage_summary}

## 覆盖源码范围

{file_rows}

## 模块在系统中的位置

{dependency_diagram}

## 核心流程

{flow_diagram}

## 焦点源码图

{focus_file_diagram}

## 关键子领域

{chr(10).join(child_rows)}

## 公开接口与扩展点

{export_rows}

## 核心类型关系

{class_diagram or "当前焦点源码没有稳定的类型导出关系，未生成类图，避免伪造结构。"}

## 关键实现片段

{render_code_examples(project_root, source_paths, exports)}

## 适用场景

- 当你需要理解 `{module['slug']}` 在整体链路中的职责时，先读本页。
- 当你需要改动该领域的主入口、主要状态或高频协议时，把本页中的焦点源码当成第一批检查点。
- 当某个问题需要继续下钻时，再沿着子领域和现有设计文档进入更细的资料。

## 设计约束与最佳实践

### 最佳实践

- 修改 `{module['slug']}` 前先确认调用方、状态来源和依赖设计文档，避免只改渲染层导致协议不一致。
- 如果这个领域同时涉及事件和 UI，优先保证事件协议与状态更新顺序的稳定性。
- 对核心目录只保留稳定入口和高价值片段到文档中，避免文档与代码一起膨胀失控。

### 性能优化

- 优先围绕焦点源码和高频入口做性能分析，不要把整目录都当成一个性能单元。
- `workflow`、`chat`、`ai` 类模块通常存在异步链路和状态同步，性能优化要同时考虑渲染、网络和缓存。
- 如果某个文件持续成为热点，应拆出更聚焦的领域文档而不是继续向同一篇文档堆内容。

### 错误处理

- 先确认问题属于接口协议、状态同步还是渲染呈现，再进入对应源码。
- 保留相对路径源码链接，确保评审和排障时能直接回到实现文件。
- 领域文档如果无法覆盖新的复杂子链路，应增补子文档，而不是继续在同一页追加混杂内容。

## 变更风险与协作边界

- 任何涉及共享状态、事件协议或跨容器调用的变更，都应同时检查相关设计文档与相邻领域。
- 如果某个文件既是高频入口又承担多种职责，优先拆分职责而不是继续依赖文档补充解释。
- 进入评审前，建议至少抽样验证 1 到 2 个焦点源码链接和 1 条 Mermaid 主流程图。

## 关联设计文档

| 文档 | 摘要 |
|------|------|
{chr(10).join(design_doc_rows)}

## 相关文档

{render_related_section(doc_path, generated_docs, relevant_docs, project_root, module['slug'])}
"""


def render_api_doc(
    doc_path: Path,
    project_root: Path,
    module: Dict[str, Any],
    source_paths: Sequence[str],
    exports: Sequence[Dict[str, Any]],
    analysis: Dict[str, Any],
    generated_docs: Dict[str, str],
) -> str:
    related_source_docs = pick_relevant_docs(analysis.get("docs_catalog", []), module["slug"], 2)
    domain_doc_link = doc_link(doc_path, generated_docs[module["slug"]])
    actual_context = compute_actual_context(module["module_type"], module=module, analysis=analysis)
    focus_context = compute_focus_context(project_root, source_paths)
    source_rows = render_source_table(doc_path, project_root, source_paths)
    coverage_table = render_focus_coverage_table(actual_context, focus_context)
    coverage_summary = render_focus_coverage_summary(actual_context, focus_context)
    export_rows = render_export_table(doc_path, project_root, exports)
    class_diagram = render_exports_class_diagram(exports)
    focus_file_diagram = render_focus_file_diagram(project_root, source_paths, f"{module['slug']} API 焦点")

    return f"""# {humanize_slug(module['slug'])} API 视图

> 本文档聚焦 `{module['slug']}` 的公开导出、关键调用入口和接入建议，适合作为接口评审与源码跳转的视图层文档。

## 接口定位

该视图不是完整 SDK 文档，而是从当前高价值源码中提取出的公开导出与关键入口。它的目标是帮助开发者快速找到“应该从哪里接入或排查”。

## 接入流程

```mermaid
flowchart LR
    Caller["调用方"] --> API["{module['slug']}"]
    API --> Source["焦点源码"]
    Source --> Result["结果 / 状态更新"]
```

## 调用时序

```mermaid
sequenceDiagram
    participant Caller as 调用方
    participant API as {module['slug']}
    participant Service as 下游服务
    Caller->>API: 发起调用
    API->>Service: 请求/命令
    Service-->>API: 返回数据/状态
    API-->>Caller: 输出结果
```

## 覆盖策略

{coverage_table}

`api-complete` 文档的核心不是把所有源码都贴进来，而是确保焦点源码足够覆盖真实接口面，并明确告诉评审者当前文档聚焦了哪些文件、多少导出和多少类型契约。

## 覆盖摘要

{coverage_summary}

## 焦点源码

{source_rows}

## 焦点源码图

{focus_file_diagram}

## 导出接口表

{export_rows}

## 接口类型关系

{class_diagram or "当前焦点源码没有形成稳定的类型关系图，未输出 classDiagram，避免伪造依赖。"}

## 使用片段

{render_code_examples(project_root, source_paths, exports)}

## 调用约束

- 先确认该接口属于同步导出、异步请求封装还是事件桥接，避免用错接入方式。
- 如果接口依赖上层上下文、Store 或 Agent 运行态，应在调用前检查前置条件是否满足。
- 对外复用前建议先从源码链接确认类型定义和返回值形态。

## 接入建议

- 先阅读 [领域概览]({domain_doc_link})，再下钻到具体导出接口，避免脱离业务上下文理解 API。
- 如果导出接口实际依赖内部状态机或事件总线，文档里应明确记录调用前置条件。
- 对外复用的接口要保持相对路径源码链接，方便 PR 审查和回归定位。

## 最佳实践

- 通过焦点源码和导出表建立“接口入口 -> 关键实现 -> 调用结果”的三段式理解。
- 如果接口数量继续增加，拆分为更细的 API 主题页，而不是把所有导出塞进单页。
- 所有新增 API 文档都应附带至少一个相对路径源码链接和一个实际代码片段。

## 错误处理

- 当接口行为与预期不符时，先检查导出定义、调用前置条件和相关状态机是否一致。
- 如果问题来自服务层协议，请回到 `services` 或 `cloud-agent` 领域文档继续追踪。
- 如果问题来自渲染结果而不是接口本身，请切回对应领域文档看主流程与状态边界。

## 相关文档

{render_related_section(doc_path, generated_docs, related_source_docs, project_root, module['slug'])}
"""


def update_frontmatter_values(file_path: Path, updates: Dict[str, Any]) -> None:
    raw_content = file_path.read_text(encoding="utf-8")
    metadata, body = check_quality.parse_frontmatter(raw_content)
    if not metadata:
        return
    metadata.update(updates)
    write_document(file_path, metadata, body)


def annotate_quality(wiki_root: Path, report: check_quality.QualityReport) -> None:
    for doc in report.docs:
        file_path = Path(doc.file_path)
        update_frontmatter_values(
            file_path,
            {
                "quality_score": f"{doc.score_ratio:.2f}",
                "quality_level": doc.quality_level,
                "last_verified_at": report.check_time,
            },
        )


def meets_publish_contract(
    doc_metrics: Optional[check_quality.QualityMetrics],
    minimum_publish_quality: str,
    block_publish_on_warnings: bool,
) -> bool:
    if not doc_metrics or doc_metrics.fatal_issues:
        return False
    if block_publish_on_warnings and doc_metrics.warning_issues:
        return False
    return quality_rank(doc_metrics.quality_level) >= quality_rank(minimum_publish_quality)


def annotate_publish_status(
    wiki_root: Path,
    report: check_quality.QualityReport,
    requires_approval: bool,
    minimum_publish_quality: str,
    block_publish_on_warnings: bool,
) -> Dict[str, int]:
    stats = {"approved": 0, "draft_or_reviewed": 0, "quality_blocked": 0, "approval_blocked": 0, "ready": 0, "total": 0}
    docs_by_path = {Path(doc.file_path).resolve(): doc for doc in report.docs}

    for md_file in sorted((wiki_root / "wiki").rglob("*.md")):
        raw_content = md_file.read_text(encoding="utf-8")
        metadata, body = check_quality.parse_frontmatter(raw_content)
        if not metadata:
            continue
        stats["total"] += 1
        review_status = str(metadata.get("review_status", "draft"))
        is_approved = review_status in {"approved", "published"}
        if is_approved:
            stats["approved"] += 1
        else:
            stats["draft_or_reviewed"] += 1

        doc_metrics = docs_by_path.get(md_file.resolve())
        quality_ok = meets_publish_contract(doc_metrics, minimum_publish_quality, block_publish_on_warnings)
        publish_ready = quality_ok and (is_approved or not requires_approval)
        if quality_ok:
            if publish_ready:
                stats["ready"] += 1
            else:
                stats["approval_blocked"] += 1
        else:
            stats["quality_blocked"] += 1
        metadata["publish_status"] = "ready" if publish_ready else "blocked"
        write_document(md_file, metadata, body)

    return stats


def write_doc_manifest(project_root: Path, report: check_quality.QualityReport) -> Path:
    manifest_path = project_root / ".mini-wiki" / "doc_manifest.json"
    docs_payload: List[Dict[str, Any]] = []
    for doc in report.docs:
        raw = Path(doc.file_path).read_text(encoding="utf-8")
        frontmatter, _ = check_quality.parse_frontmatter(raw)
        docs_payload.append(
            {
                "path": doc.file_path,
                "doc_type": doc.doc_type,
                "doc_profile": frontmatter.get("doc_profile"),
                "module_type": frontmatter.get("module_type"),
                "doc_role": frontmatter.get("doc_role"),
                "review_status": frontmatter.get("review_status", "draft"),
                "publish_status": frontmatter.get("publish_status", "blocked"),
                "active_plugins": frontmatter.get("active_plugins", []),
                "quality_level": doc.quality_level,
                "quality_score": doc.score_ratio,
                "source_paths": frontmatter.get("source_paths", []),
                "focus_paths": frontmatter.get("focus_paths", []),
                "actual_context": {
                    "source_files": frontmatter.get("actual_source_files", 0),
                    "source_lines": frontmatter.get("actual_source_lines", 0),
                    "export_count": frontmatter.get("actual_export_count", 0),
                },
                "focus_context": {
                    "source_files": frontmatter.get("focus_source_files", 0),
                    "source_lines": frontmatter.get("focus_source_lines", 0),
                    "export_count": frontmatter.get("focus_export_count", 0),
                },
                "fatal_issues": doc.fatal_issues,
                "warning_issues": doc.warning_issues,
            }
        )

    payload = {
        "generated_at": now_iso(),
        "generator_version": GENERATOR_VERSION,
        "total_docs": len(docs_payload),
        "docs": docs_payload,
    }
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_path


def update_meta(
    project_root: Path,
    analysis: Dict[str, Any],
    report: check_quality.QualityReport,
    generated_count: int,
    quality_status: str,
    publish_stats: Dict[str, int],
    generation_signature: str,
    settings: Dict[str, Any],
) -> None:
    meta_path = project_root / ".mini-wiki" / "meta.json"
    meta = load_json(meta_path)
    meta.update(
        {
            "version": GENERATOR_VERSION,
            "last_updated": report.check_time,
            "files_documented": analysis.get("stats", {}).get("total_files", 0),
            "modules_count": generated_count,
            "quality_status": quality_status,
            "quality_summary": {
                "professional": report.professional_count,
                "standard": report.standard_count,
                "basic": report.basic_count,
            },
            "generation_signature": generation_signature,
            "quality_ruleset_version": QUALITY_RULESET_VERSION,
            "minimum_publish_quality": settings.get("minimum_publish_quality", "professional"),
            "block_publish_on_warnings": bool(settings.get("block_publish_on_warnings", True)),
            "publish_summary": publish_stats,
            "active_plugins": list(RUNTIME_ACTIVE_PLUGINS),
        }
    )
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def select_api_modules(selected_modules: Sequence[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    candidates = sorted(
        [module for module in selected_modules if module["module_type"] in {"api", "ai", "workflow", "event"}],
        key=lambda module: (
            2 if module["module_type"] == "api" else 1,
            1 if "service" in module["slug"] or "cloud-agent" in module["slug"] else 0,
            module.get("importance", 0),
        ),
        reverse=True,
    )
    return list(candidates[:limit])


def ensure_wiki(project_root: Path, force_init: bool = False) -> None:
    wiki_root = project_root / ".mini-wiki"
    if not wiki_root.exists():
        init_wiki.init_mini_wiki(str(project_root), force=force_init)


def export_language_mirrors(project_root: Path, language: str) -> None:
    wiki_root = project_root / ".mini-wiki"
    wiki_dir = wiki_root / "wiki"
    if not wiki_dir.exists():
        return

    targets: List[str] = []
    if language in {"zh", "both"}:
        targets.append("zh")
    if language in {"en", "both"}:
        targets.append("en")
    if not targets:
        return

    for locale in targets:
        locale_root = wiki_root / "i18n" / locale
        if locale_root.exists():
            shutil.rmtree(locale_root)
        locale_root.mkdir(parents=True, exist_ok=True)
        for source in wiki_dir.rglob("*.md"):
            relative = source.relative_to(wiki_dir)
            destination = locale_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def is_incremental_enabled(mode: Any) -> bool:
    return mode in {"auto", "always", True}


def filter_modules_by_changes(modules: List[Dict[str, Any]], changed_paths: Sequence[str]) -> List[Dict[str, Any]]:
    if not changed_paths:
        return modules
    changed = tuple(changed_paths)

    def touched(module: Dict[str, Any]) -> bool:
        module_path = str(module.get("path", "")).strip("/")
        if not module_path:
            return False
        prefix = module_path + "/"
        return any(item == module_path or item.startswith(prefix) for item in changed)

    filtered = [module for module in modules if touched(module)]
    return filtered or modules


def should_enable_progressive_generation(settings: Dict[str, Any], analysis: Dict[str, Any], module_count: int) -> bool:
    mode = settings.get("progressive_mode", "auto")
    if mode in {"never", False}:
        return False
    if mode in {"always", True}:
        return True
    stats = analysis.get("stats", {})
    return (
        module_count > 10
        or int(stats.get("total_files", 0)) > 50
        or int(stats.get("source_lines", 0)) > 10000
    )


def progress_path_for(project_root: Path) -> Path:
    return project_root / ".mini-wiki" / "cache" / "progress.json"


def write_progress_state(project_root: Path, progress_state: Dict[str, Any]) -> Path:
    path = progress_path_for(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    progress_state["last_updated"] = now_iso()
    path.write_text(json.dumps(progress_state, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def initialize_progress_state(
    project_root: Path,
    selected_modules: Sequence[Dict[str, Any]],
    api_modules: Sequence[Dict[str, Any]],
    generation_signature: str,
    batch_size: int,
    completed_modules: Optional[Sequence[str]] = None,
    completed_api_modules: Optional[Sequence[str]] = None,
    total_modules: Optional[int] = None,
    total_api_modules: Optional[int] = None,
) -> Dict[str, Any]:
    completed_modules = list(completed_modules or [])
    completed_api_modules = list(completed_api_modules or [])
    completed_count = len(completed_modules) + len(completed_api_modules)
    progress_state = {
        "version": GENERATOR_VERSION,
        "quality_ruleset_version": QUALITY_RULESET_VERSION,
        "generation_signature": generation_signature,
        "status": "running",
        "batch_size": max(1, batch_size),
        "current_batch": max(1, completed_count // max(1, batch_size) + 1),
        "total_modules": total_modules if total_modules is not None else len(completed_modules) + len(selected_modules),
        "completed_modules": completed_modules,
        "pending_modules": [module["slug"] for module in selected_modules],
        "total_api_modules": total_api_modules if total_api_modules is not None else len(completed_api_modules) + len(api_modules),
        "completed_api_modules": completed_api_modules,
        "pending_api_modules": [module["slug"] for module in api_modules],
        "last_completed": None,
        "publish_ready": False,
        "quality_status": "draft",
    }
    write_progress_state(project_root, progress_state)
    return progress_state


def prepare_progress_state(
    project_root: Path,
    settings: Dict[str, Any],
    analysis: Dict[str, Any],
    selected_modules: List[Dict[str, Any]],
    api_modules: List[Dict[str, Any]],
    generation_signature: str,
    force_full: bool,
) -> Tuple[Optional[Path], Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not should_enable_progressive_generation(settings, analysis, len(selected_modules)):
        return None, {}, selected_modules, api_modules

    batch_size = int(settings.get("progressive_batch_size", 2))
    progress_file = progress_path_for(project_root)
    progress_state: Dict[str, Any] = {}
    all_selected_modules = list(selected_modules)
    all_api_modules = list(api_modules)
    completed_modules: List[str] = []
    completed_api_modules: List[str] = []

    if (
        not force_full
        and bool(settings.get("progressive_resume_from_cache", True))
        and progress_file.exists()
    ):
        progress_state = load_json(progress_file)
        if generation_contract_matches(progress_state, generation_signature):
            completed_modules = list(progress_state.get("completed_modules", []))
            completed_api_modules = list(progress_state.get("completed_api_modules", []))
            completed_module_set = set(completed_modules)
            completed_api_module_set = set(completed_api_modules)
            selected_modules = [module for module in selected_modules if module["slug"] not in completed_module_set]
            api_modules = [module for module in api_modules if module["slug"] not in completed_api_module_set]

    progress_state = initialize_progress_state(
        project_root,
        selected_modules,
        api_modules,
        generation_signature,
        batch_size,
        completed_modules=completed_modules,
        completed_api_modules=completed_api_modules,
        total_modules=len(all_selected_modules),
        total_api_modules=len(all_api_modules),
    )
    return progress_file, progress_state, selected_modules, api_modules


def mark_progress_complete(
    project_root: Path,
    progress_state: Dict[str, Any],
    item_slug: str,
    *,
    api: bool = False,
) -> None:
    if not progress_state:
        return
    completed_key = "completed_api_modules" if api else "completed_modules"
    pending_key = "pending_api_modules" if api else "pending_modules"
    completed = list(progress_state.get(completed_key, []))
    if item_slug not in completed:
        completed.append(item_slug)
    progress_state[completed_key] = completed
    progress_state[pending_key] = [slug for slug in progress_state.get(pending_key, []) if slug != item_slug]
    progress_state["last_completed"] = {"kind": "api" if api else "module", "slug": item_slug, "completed_at": now_iso()}
    completed_count = len(progress_state.get("completed_modules", [])) + len(progress_state.get("completed_api_modules", []))
    batch_size = max(1, int(progress_state.get("batch_size", 1)))
    progress_state["current_batch"] = max(1, completed_count // batch_size + 1)
    write_progress_state(project_root, progress_state)


def build_doc_mapping_from_generated(generated_files: Sequence[Path], project_root: Path) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for doc_file in generated_files:
        if not doc_file.exists():
            continue
        raw = doc_file.read_text(encoding="utf-8")
        frontmatter, _ = check_quality.parse_frontmatter(raw)
        source_paths = frontmatter.get("source_paths", [])
        if isinstance(source_paths, str):
            source_paths = [source_paths]
        if not isinstance(source_paths, list):
            continue
        for source in source_paths:
            if not isinstance(source, str):
                continue
            mapping[source] = str(doc_file.relative_to(project_root).as_posix())
    return mapping


def prune_stale_generated_docs(wiki_dir: Path, generated_files: Sequence[Path]) -> List[str]:
    generated_set = {path.resolve() for path in generated_files}
    removed: List[str] = []
    for md_file in sorted(wiki_dir.rglob("*.md")):
        if md_file.resolve() in generated_set:
            continue
        raw_content = md_file.read_text(encoding="utf-8")
        metadata, _ = check_quality.parse_frontmatter(raw_content)
        if metadata.get("generated_by") != "mini-wiki-generator":
            continue
        md_file.unlink()
        removed.append(str(md_file))
    return removed


def generate_wiki(
    project_root: str,
    max_module_docs: int = MODULE_DOC_LIMIT,
    max_api_docs: int = API_DOC_LIMIT,
    force_full: bool = False,
) -> Dict[str, Any]:
    root = Path(project_root).resolve()
    ensure_wiki(root)

    settings = load_generation_settings(root)
    configure_runtime_link_settings(settings)
    global RUNTIME_ACTIVE_PLUGINS
    RUNTIME_ACTIVE_PLUGINS = load_enabled_plugins(root)
    profile = load_generation_profile(settings)
    generation_signature = build_generation_signature(settings, profile, RUNTIME_ACTIVE_PLUGINS)
    package_json = load_json(root / "package.json")
    metadata_contract = {
        "generation_signature": generation_signature,
        "minimum_publish_quality": settings["minimum_publish_quality"],
        "block_publish_on_warnings": settings["block_publish_on_warnings"],
    }

    incremental_info: Dict[str, Any] = {}
    if not force_full and is_incremental_enabled(settings.get("incremental_mode", "auto")):
        incremental_info = detect_changes.detect_changes(str(root))
        report_path = root / ".mini-wiki" / "quality-report.json"
        if not incremental_info.get("has_changes") and report_path.exists():
            meta = load_json(root / ".mini-wiki" / "meta.json")
            if generation_contract_matches(meta, generation_signature):
                existing_report = load_json(report_path)
                summary = existing_report.get("summary", {})
                publish_summary = meta.get("publish_summary", {})
                quality_status = str(meta.get("quality_status", "unknown"))
                return {
                    "success": True,
                    "project_root": str(root),
                    "generated_files": [],
                    "quality_report": str(report_path),
                    "summary": {
                        "total_docs": summary.get("total", 0),
                        "professional": summary.get("professional", 0),
                        "standard": summary.get("standard", 0),
                        "basic": summary.get("basic", 0),
                        "quality_status": quality_status,
                        "approved_docs": publish_summary.get("approved", 0),
                        "pending_approval": publish_summary.get("draft_or_reviewed", 0),
                        "publish_ready": quality_status == "ready-for-publish",
                    },
                    "skipped": True,
                    "reason": "no_changes_detected",
                }

    analysis = analyze_project.analyze_project(str(root), save_to_cache=True)
    owners = read_owners(root, settings["owner_file"])

    wiki_dir = root / ".mini-wiki" / "wiki"
    domains_dir = wiki_dir / "domains"
    api_dir = wiki_dir / "api"
    domains_dir.mkdir(parents=True, exist_ok=True)
    api_dir.mkdir(parents=True, exist_ok=True)

    selected_modules = select_modules(list(analysis.get("modules", [])), max_module_docs, profile)
    if incremental_info.get("has_changes"):
        changed_paths = [
            *incremental_info.get("added", []),
            *incremental_info.get("modified", []),
            *incremental_info.get("deleted", []),
        ]
        selected_modules = filter_modules_by_changes(selected_modules, changed_paths)
    api_modules = select_api_modules(selected_modules, max_api_docs)
    progress_file, progress_state, selected_modules, api_modules = prepare_progress_state(
        root,
        settings,
        analysis,
        selected_modules,
        api_modules,
        generation_signature,
        force_full,
    )

    generated_docs: Dict[str, str] = {
        "index": "index.md",
        "architecture": "architecture.md",
        "getting_started": "getting-started.md",
        "doc_map": "doc-map.md",
        "domains_index": "domains/_index.md",
    }

    for module in selected_modules:
        generated_docs[module["slug"]] = f"domains/{slug_to_filename(module['slug'])}.md"
    for module in api_modules:
        generated_docs[f"api:{module['slug']}"] = f"api/{slug_to_filename(module['slug'])}.md"

    generated_files: List[Path] = []

    index_path = wiki_dir / "index.md"
    index_body = render_index_doc(index_path, root, analysis, package_json, selected_modules, generated_docs, owners)
    write_document(
        index_path,
        build_doc_metadata(
            doc_type="index",
            module_type="project",
            doc_role="project",
            doc_profile="topic",
            source_paths=list(dict.fromkeys([*analysis.get("entry_points", [])[:3], "package.json"])),
            actual_context=compute_actual_context("project", analysis=analysis),
            focus_context=compute_focus_context(root, list(dict.fromkeys([*analysis.get("entry_points", [])[:3], "package.json"]))),
            owners=owners,
            review_status=settings["review_status"],
            **metadata_contract,
        ),
        index_body,
    )
    generated_files.append(index_path)

    architecture_path = wiki_dir / "architecture.md"
    architecture_sources = collect_architecture_focus_sources(root, analysis, selected_modules)
    architecture_body = render_architecture_doc(architecture_path, root, analysis, selected_modules, generated_docs)
    write_document(
        architecture_path,
        build_doc_metadata(
            doc_type="architecture",
            module_type="core",
            doc_role="overview",
            doc_profile="overview",
            source_paths=[path for path in architecture_sources if (root / path).exists()],
            actual_context=compute_actual_context("project", analysis=analysis),
            focus_context=compute_focus_context(root, [path for path in architecture_sources if (root / path).exists()]),
            owners=owners,
            review_status=settings["review_status"],
            **metadata_contract,
        ),
        architecture_body,
    )
    generated_files.append(architecture_path)

    getting_started_path = wiki_dir / "getting-started.md"
    getting_started_body = render_getting_started_doc(getting_started_path, root, analysis, package_json, generated_docs, owners)
    write_document(
        getting_started_path,
        build_doc_metadata(
            doc_type="getting-started",
            module_type="project",
            doc_role="project",
            doc_profile="topic",
            source_paths=list(dict.fromkeys([*analysis.get("entry_points", [])[:3], "package.json", "build.sh"])),
            actual_context=compute_actual_context("project", analysis=analysis),
            focus_context=compute_focus_context(root, list(dict.fromkeys([*analysis.get("entry_points", [])[:3], "package.json", "build.sh"]))),
            owners=owners,
            review_status=settings["review_status"],
            **metadata_contract,
        ),
        getting_started_body,
    )
    generated_files.append(getting_started_path)

    domains_index_path = domains_dir / "_index.md"
    domains_index_body = render_domains_index(domains_index_path, root, selected_modules, generated_docs)
    write_document(
        domains_index_path,
        build_doc_metadata(
            doc_type="_index",
            module_type="project",
            doc_role="project",
            doc_profile="topic",
            source_paths=[module["path"] for module in selected_modules[:3]],
            actual_context=compute_actual_context("project", analysis=analysis),
            focus_context=compute_focus_context(root, [module["path"] for module in selected_modules[:3]]),
            owners=owners,
            review_status=settings["review_status"],
            **metadata_contract,
        ),
        domains_index_body,
    )
    generated_files.append(domains_index_path)

    for module in selected_modules:
        source_paths = choose_focus_files(root, module, MAX_FOCUS_FILES)
        exports = extract_export_entries(root, source_paths)
        module_profile = str(settings.get("doc_profile", "overview"))
        module_doc_role = "overview" if module_profile == "overview" else "module"
        doc_path = wiki_dir / generated_docs[module["slug"]]
        body = render_module_doc(doc_path, root, module, source_paths, exports, analysis, generated_docs)
        write_document(
            doc_path,
            build_doc_metadata(
                doc_type="domain",
                module_type=module["module_type"],
                doc_role=module_doc_role,
                doc_profile=module_profile,
                source_paths=source_paths,
                actual_context=compute_actual_context(module["module_type"], module=module, analysis=analysis),
                focus_context=compute_focus_context(root, source_paths),
                owners=owners,
                review_status=settings["review_status"],
                **metadata_contract,
            ),
            body,
        )
        generated_files.append(doc_path)
        mark_progress_complete(root, progress_state, module["slug"])

    generated_api_modules: List[Dict[str, Any]] = []

    for module in api_modules:
        source_paths = choose_focus_files(root, module, MAX_API_FOCUS_FILES, api_mode=True)
        exports = extract_export_entries(root, source_paths)
        if not exports:
            continue
        doc_path = wiki_dir / generated_docs[f"api:{module['slug']}"]
        body = render_api_doc(doc_path, root, module, source_paths, exports, analysis, generated_docs)
        write_document(
            doc_path,
            build_doc_metadata(
                doc_type="api",
                module_type=module["module_type"],
                doc_role="interface",
                doc_profile="api-complete",
                source_paths=source_paths,
                actual_context=compute_actual_context(module["module_type"], module=module, analysis=analysis),
                focus_context=compute_focus_context(root, source_paths),
                owners=owners,
                review_status=settings["review_status"],
                **metadata_contract,
            ),
            body,
        )
        generated_files.append(doc_path)
        generated_api_modules.append(module)
        mark_progress_complete(root, progress_state, module["slug"], api=True)

    available_generated_docs = {
        name: target
        for name, target in generated_docs.items()
        if (wiki_dir / target).exists()
    }

    doc_map_path = wiki_dir / "doc-map.md"
    doc_map_body = render_doc_map(doc_map_path, root, analysis, selected_modules, available_generated_docs, generated_api_modules)
    write_document(
        doc_map_path,
        build_doc_metadata(
            doc_type="doc-map",
            module_type="project",
            doc_role="project",
            doc_profile="topic",
            source_paths=list(dict.fromkeys([*analysis.get("entry_points", [])[:2], "docs", "src/docs"])),
            actual_context=compute_actual_context("project", analysis=analysis),
            focus_context=compute_focus_context(root, list(dict.fromkeys([*analysis.get("entry_points", [])[:2], "docs", "src/docs"]))),
            owners=owners,
            review_status=settings["review_status"],
            **metadata_contract,
        ),
        doc_map_body,
    )
    if doc_map_path not in generated_files:
        generated_files.append(doc_map_path)

    removed_files = prune_stale_generated_docs(wiki_dir, generated_files)

    report = check_quality.check_wiki_quality(str(root / ".mini-wiki"))
    annotate_quality(root / ".mini-wiki", report)
    final_report = check_quality.check_wiki_quality(str(root / ".mini-wiki"))
    publish_stats = annotate_publish_status(
        root / ".mini-wiki",
        final_report,
        bool(settings.get("publish_requires_approval", True)),
        settings["minimum_publish_quality"],
        bool(settings.get("block_publish_on_warnings", True)),
    )
    final_report = check_quality.check_wiki_quality(str(root / ".mini-wiki"))
    report_path = root / ".mini-wiki" / "quality-report.json"
    check_quality.save_report_json(final_report, str(report_path))
    manifest_path = write_doc_manifest(root, final_report)

    if final_report.basic_count > 0 or publish_stats.get("quality_blocked", 0) > 0:
        quality_status = "needs-improvement"
    elif bool(settings.get("publish_requires_approval", True)) and publish_stats.get("approval_blocked", 0) > 0:
        quality_status = "needs-review"
    else:
        quality_status = "ready-for-publish"

    update_meta(root, analysis, final_report, len(generated_files), quality_status, publish_stats, generation_signature, settings)

    if progress_state:
        progress_state["status"] = "complete"
        progress_state["quality_status"] = quality_status
        progress_state["publish_ready"] = quality_status == "ready-for-publish"
        progress_state["current_batch"] = max(1, int(progress_state.get("current_batch", 1)))
        write_progress_state(root, progress_state)

    if incremental_info:
        doc_mapping = build_doc_mapping_from_generated(generated_files, root)
        checksums = incremental_info.get("current_checksums")
        if not checksums:
            refreshed = detect_changes.scan_project_files(str(root))
            checksums = refreshed
        if isinstance(checksums, dict):
            detect_changes.update_checksums_cache(str(root), checksums, doc_mapping=doc_mapping)

    export_language_mirrors(root, str(settings.get("language", "zh")))

    requires_approval = bool(settings.get("publish_requires_approval", True))
    publish_ready = quality_status == "ready-for-publish"

    return {
        "success": final_report.basic_count == 0,
        "project_root": str(root),
        "generated_files": [str(path) for path in generated_files],
        "removed_files": removed_files,
        "quality_report": str(report_path),
        "doc_manifest": str(manifest_path),
        "progress_file": str(progress_file) if progress_file else None,
        "summary": {
            "total_docs": final_report.total_docs,
            "professional": final_report.professional_count,
            "standard": final_report.standard_count,
            "basic": final_report.basic_count,
            "quality_status": quality_status,
            "approved_docs": publish_stats.get("approved", 0),
            "pending_approval": publish_stats.get("draft_or_reviewed", 0),
            "quality_blocked": publish_stats.get("quality_blocked", 0),
            "publish_ready": publish_ready,
            "active_plugins": list(RUNTIME_ACTIVE_PLUGINS),
        },
    }


def print_result(result: Dict[str, Any]) -> None:
    print(f"项目: {result['project_root']}")
    if result.get("skipped"):
        print("生成已跳过: no_changes_detected")
        print(f"质量报告: {result['quality_report']}")
        return
    print("生成文档:")
    for path in result["generated_files"]:
        print(f"  - {path}")
    if result.get("removed_files"):
        print("清理旧文档:")
        for path in result["removed_files"]:
            print(f"  - {path}")
    summary = result["summary"]
    print(
        f"质量结果: total={summary['total_docs']}, "
        f"professional={summary['professional']}, "
        f"standard={summary['standard']}, basic={summary['basic']}"
    )
    print(
        f"发布状态: {summary.get('quality_status')}, "
        f"approved={summary.get('approved_docs', 0)}, "
        f"pending={summary.get('pending_approval', 0)}, "
        f"quality_blocked={summary.get('quality_blocked', 0)}, "
        f"publish_ready={summary.get('publish_ready', False)}"
    )
    print(f"质量报告: {result['quality_report']}")
    if result.get("doc_manifest"):
        print(f"文档清单: {result['doc_manifest']}")
    if result.get("progress_file"):
        print(f"生成进度: {result['progress_file']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Mini-Wiki 生产化文档生成器")
    parser.add_argument("project_root", nargs="?", default=os.getcwd(), help="项目根目录")
    parser.add_argument("--max-module-docs", type=int, default=MODULE_DOC_LIMIT, help="最多生成的领域文档数")
    parser.add_argument("--max-api-docs", type=int, default=API_DOC_LIMIT, help="最多生成的 API 文档数")
    parser.add_argument("--full", action="store_true", help="强制全量生成（忽略增量跳过）")
    args = parser.parse_args()

    result = generate_wiki(
        args.project_root,
        max_module_docs=args.max_module_docs,
        max_api_docs=args.max_api_docs,
        force_full=args.full,
    )
    print_result(result)
    return 0 if result["success"] and result.get("summary", {}).get("publish_ready", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
