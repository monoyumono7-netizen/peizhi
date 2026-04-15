#!/usr/bin/env python3
"""
Mini-Wiki quality gate.

This implementation enforces dynamic expectations based on source complexity
instead of a fixed point system, making the output suitable for CI and
production documentation reviews.
"""

import argparse
import json
import math
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config_utils import DEFAULT_FILE_EXCLUDE_PATTERNS, get_effective_excludes, path_matches_patterns

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

INDEX_DOCS = {"index", "_index", "doc-map", "getting-started"}
PROJECT_DOCS = {"index", "_index", "doc-map", "getting-started", "architecture"}
REQUIRED_SOURCE_DOCS = {"architecture", "module", "api", "domain"}
ROLE_WEIGHTS = {
    "core": 4,
    "workflow": 4,
    "ai": 4,
    "api": 4,
    "state": 3,
    "event": 3,
    "routing": 3,
    "ui": 3,
    "media": 3,
    "utility": 2,
    "hooks": 2,
    "module": 2,
    "types": 1,
    "config": 1,
    "test": 0,
}


@dataclass
class QualityMetrics:
    file_path: str
    doc_type: str = "module"
    doc_profile: str = "overview"
    line_count: int = 0
    section_count: int = 0
    subsection_count: int = 0
    diagram_count: int = 0
    class_diagram_count: int = 0
    sequence_diagram_count: int = 0
    state_diagram_count: int = 0
    code_example_count: int = 0
    table_count: int = 0
    cross_link_count: int = 0
    source_link_count: int = 0
    has_source_tracing: bool = False
    has_best_practices: bool = False
    has_performance: bool = False
    has_troubleshooting: bool = False
    has_related_docs: bool = False
    has_unreplaced_templates: bool = False
    mermaid_issues: int = 0
    quality_level: str = "basic"
    score_ratio: float = 0.0
    content_score: float = 0.0
    coverage_score: float = 0.0
    traceability_score: float = 0.0
    expected_metrics: Dict[str, Any] = field(default_factory=dict)
    source_context: Dict[str, Any] = field(default_factory=dict)
    fatal_issues: List[str] = field(default_factory=list)
    warning_issues: List[str] = field(default_factory=list)

    @property
    def issues(self) -> List[str]:
        return [*self.fatal_issues, *self.warning_issues]


@dataclass
class QualityReport:
    wiki_path: str
    check_time: str
    total_docs: int = 0
    professional_count: int = 0
    standard_count: int = 0
    basic_count: int = 0
    docs: List[QualityMetrics] = field(default_factory=list)
    summary_issues: List[str] = field(default_factory=list)


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    if not content.startswith("---\n"):
        return {}, content

    end = content.find("\n---", 4)
    if end == -1:
        return {}, content

    frontmatter = content[4:end].splitlines()
    body = content[end + 4 :].lstrip("\n")
    data: Dict[str, Any] = {}
    current_list_key: Optional[str] = None

    for raw_line in frontmatter:
        line = raw_line.rstrip()
        if not line or line.strip().startswith("#"):
            continue
        if line.startswith("  - ") or line.startswith("- "):
            if current_list_key:
                data.setdefault(current_list_key, []).append(line.split("- ", 1)[1].strip().strip("'\""))
            continue
        current_list_key = None
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            data[key] = []
            current_list_key = key
            continue
        data[key] = value.strip("'\"")

    return data, body


def normalize_doc_key(value: str) -> str:
    normalized = value.replace("\\", "/").strip("/")
    if normalized.startswith("src/"):
        normalized = normalized[4:]
    if normalized.endswith(".md"):
        normalized = normalized[:-3]
    return normalized


def classify_doc_type(file_path: Path) -> str:
    relative = normalize_doc_key(str(file_path))
    base = file_path.stem
    if "/api/" in relative or file_path.parent.name == "api":
        return "api"
    if base in INDEX_DOCS:
        return base
    if base == "architecture":
        return "architecture"
    if file_path.parent.name not in {"wiki", "api"}:
        return "domain"
    return "module"


def check_template_completeness(content: str) -> List[str]:
    placeholders = re.findall(r"\{\{\s*(\w+)\s*\}\}", content)
    return [f"未替换的模板变量: {{{{ {placeholder} }}}}" for placeholder in placeholders]


def validate_mermaid_blocks(content: str) -> List[str]:
    issues: List[str] = []
    blocks = re.findall(r"```mermaid\s*\n([\s\S]*?)```", content)
    valid_types = {
        "flowchart",
        "graph",
        "sequenceDiagram",
        "stateDiagram",
        "stateDiagram-v2",
        "classDiagram",
        "mindmap",
        "erDiagram",
        "gantt",
        "pie",
        "gitgraph",
        "journey",
        "timeline",
        "quadrantChart",
        "sankey",
        "xychart",
        "block",
    }

    for index, block in enumerate(blocks, 1):
        stripped = block.strip()
        if not stripped:
            issues.append(f"Mermaid 块 #{index} 为空")
            continue
        first_line = stripped.splitlines()[0].strip()
        if not any(first_line.startswith(kind) for kind in valid_types):
            issues.append(f"Mermaid 块 #{index} 缺少有效类型声明")
        for line_number, line in enumerate(stripped.splitlines(), 1):
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("%%"):
                continue
            if re.search(r"[\[\(][\u4e00-\u9fff][^\"\]\)]*[\]\)]", line) and '"' not in line:
                issues.append(f"Mermaid 块 #{index} 第 {line_number} 行包含未加引号的中文标签")
                break

    return issues


def count_tables(content: str) -> int:
    table_count = 0
    in_table = False
    for line in content.splitlines():
        stripped = line.strip()
        is_table_row = bool(re.match(r"^\|.*\|.*\|", stripped))
        is_separator = bool(re.match(r"^\|[\s\-:|]+\|$", stripped))
        if is_table_row and not is_separator:
            if not in_table:
                table_count += 1
                in_table = True
        elif not is_table_row and not is_separator:
            in_table = False
    return table_count


def evaluate_source_links(content: str) -> Tuple[int, bool, List[str]]:
    issues: List[str] = []
    source_links = 0
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
        if target.startswith("file://"):
            issues.append("源码追溯禁止使用 file:// 链接")
            continue
        if target.startswith(("http://", "https://")):
            if "github.com/" in target and "/blob/" in target:
                source_links += 1
            continue
        suffix = Path(target.split("#", 1)[0]).suffix
        if target.startswith(("./", "../")) and suffix and suffix != ".md":
            source_links += 1
    return source_links, source_links > 0, issues


def load_structure(wiki_path: str) -> Dict[str, Any]:
    structure_path = Path(wiki_path) / "cache" / "structure.json"
    if not structure_path.exists():
        return {}
    try:
        return json.loads(structure_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def scan_source_paths(paths: List[Path], project_root: Path) -> Dict[str, int]:
    exclude_dirs, exclude_patterns = get_effective_excludes(project_root, set(), DEFAULT_FILE_EXCLUDE_PATTERNS)
    source_files = 0
    source_lines = 0
    export_count = 0
    class_count = 0
    interface_count = 0
    for path in paths:
        if not path.exists():
            continue
        files = (
            [path]
            if path.is_file()
            else [
                item
                for item in path.rglob("*")
                if item.is_file()
                and item.suffix in CODE_EXTENSIONS
                and not any(part in exclude_dirs for part in item.parts)
                and not path_matches_patterns(item, project_root, exclude_patterns)
            ]
        )
        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            source_files += 1
            source_lines += len(content.splitlines())
            export_count += len(re.findall(r"^\s*(?:export\s|module\.exports|exports\.|pub\s+|public\s+|def\s+\w+\(|class\s+\w+)", content, re.MULTILINE))
            class_count += len(re.findall(r"^\s*(?:export\s+)?class\s+\w+", content, re.MULTILINE))
            interface_count += len(re.findall(r"^\s*(?:export\s+)?interface\s+\w+", content, re.MULTILINE))
            interface_count += len(re.findall(r"^\s*(?:export\s+)?type\s+\w+\s*=", content, re.MULTILINE))
    return {
        "source_files": source_files,
        "source_lines": source_lines,
        "export_count": export_count,
        "class_count": class_count,
        "interface_count": interface_count,
    }


def parse_int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_paths(raw_paths: Any) -> List[str]:
    if isinstance(raw_paths, str):
        return [raw_paths]
    if isinstance(raw_paths, list):
        return [item for item in raw_paths if isinstance(item, str)]
    return []


def build_source_context_from_frontmatter(frontmatter: Dict[str, Any], project_root: Path) -> Optional[Dict[str, Any]]:
    source_paths = normalize_paths(frontmatter.get("source_paths"))
    focus_paths = normalize_paths(frontmatter.get("focus_paths")) or source_paths
    has_context_fields = any(
        key in frontmatter
        for key in (
            "actual_source_files",
            "actual_source_lines",
            "actual_export_count",
            "focus_source_files",
            "focus_source_lines",
            "focus_export_count",
        )
    )

    if not has_context_fields and not focus_paths:
        return None

    focus_stats = {
        "source_files": parse_int_value(frontmatter.get("focus_source_files"), 0),
        "source_lines": parse_int_value(frontmatter.get("focus_source_lines"), 0),
        "export_count": parse_int_value(frontmatter.get("focus_export_count"), 0),
        "class_count": parse_int_value(frontmatter.get("focus_class_count"), 0),
        "interface_count": parse_int_value(frontmatter.get("focus_interface_count"), 0),
    }
    if focus_paths and focus_stats["source_files"] == 0 and focus_stats["source_lines"] == 0:
        resolved_focus = [(project_root / item).resolve() for item in focus_paths]
        focus_stats = scan_source_paths(resolved_focus, project_root)

    actual_stats = {
        "source_files": parse_int_value(frontmatter.get("actual_source_files"), 0),
        "source_lines": parse_int_value(frontmatter.get("actual_source_lines"), 0),
        "export_count": parse_int_value(frontmatter.get("actual_export_count"), 0),
        "class_count": parse_int_value(frontmatter.get("actual_class_count"), 0),
        "interface_count": parse_int_value(frontmatter.get("actual_interface_count"), 0),
    }
    if actual_stats["source_files"] == 0 and actual_stats["source_lines"] == 0:
        actual_stats = dict(focus_stats)

    doc_role = str(frontmatter.get("doc_role", "module"))
    inferred_profile = "overview" if doc_role == "overview" else "module-complete"

    return {
        "module_type": frontmatter.get("module_type", "module"),
        "doc_role": doc_role,
        "doc_profile": str(frontmatter.get("doc_profile", inferred_profile)),
        "source_paths": source_paths,
        "focus_paths": focus_paths,
        "actual_source_files": actual_stats["source_files"],
        "actual_source_lines": actual_stats["source_lines"],
        "actual_export_count": actual_stats["export_count"],
        "actual_class_count": actual_stats["class_count"],
        "actual_interface_count": actual_stats["interface_count"],
        "focus_source_files": focus_stats["source_files"],
        "focus_source_lines": focus_stats["source_lines"],
        "focus_export_count": focus_stats["export_count"],
        "focus_class_count": focus_stats["class_count"],
        "focus_interface_count": focus_stats["interface_count"],
        # Backward-compatible aliases for older callers.
        "source_files": actual_stats["source_files"],
        "source_lines": actual_stats["source_lines"],
        "export_count": actual_stats["export_count"],
    }


def match_document_to_module(
    file_path: Path,
    wiki_path: str,
    structure: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    wiki_root = Path(wiki_path) / "wiki"
    try:
        relative_doc = normalize_doc_key(str(file_path.relative_to(wiki_root)))
    except ValueError:
        relative_doc = normalize_doc_key(file_path.name)
    basename = relative_doc.split("/")[-1]
    best_match: Optional[Dict[str, Any]] = None
    best_score = -1

    for module in structure.get("modules", []):
        candidates = {
            normalize_doc_key(module.get("slug", "")),
            normalize_doc_key(module.get("path", "")),
            normalize_doc_key(module.get("name", "")),
        }
        score = 0
        if relative_doc in candidates:
            score = 3
        elif any(relative_doc.endswith(candidate) for candidate in candidates if candidate):
            score = 2
        elif basename in {candidate.split("/")[-1] for candidate in candidates if candidate}:
            score = 1
        if score > best_score:
            best_score = score
            best_match = module

    return best_match if best_score > 0 else None


def build_project_context(structure: Dict[str, Any]) -> Dict[str, Any]:
    stats = structure.get("stats", {})
    total_files = int(stats.get("total_files", 0))
    source_lines = int(stats.get("source_lines", 0))
    class_count = int(stats.get("class_count", 0))
    interface_count = int(stats.get("interface_count", 0))
    return {
        "module_type": "project",
        "doc_role": "project",
        "doc_profile": "topic",
        "actual_source_files": total_files,
        "actual_source_lines": source_lines,
        "actual_export_count": 0,
        "actual_class_count": class_count,
        "actual_interface_count": interface_count,
        "focus_source_files": total_files,
        "focus_source_lines": source_lines,
        "focus_export_count": 0,
        "focus_class_count": class_count,
        "focus_interface_count": interface_count,
        "source_files": total_files,
        "source_lines": source_lines,
        "export_count": 0,
    }


def build_source_context(
    file_path: Path,
    wiki_path: str,
    structure: Dict[str, Any],
    frontmatter: Dict[str, Any],
) -> Dict[str, Any]:
    project_root = Path(wiki_path).parent
    frontmatter_context = build_source_context_from_frontmatter(frontmatter, project_root)
    if frontmatter_context:
        return frontmatter_context

    doc_type = classify_doc_type(file_path)
    if doc_type in PROJECT_DOCS:
        return build_project_context(structure)

    module_context = match_document_to_module(file_path, wiki_path, structure)
    if module_context:
        actual_files = int(module_context.get("source_files", 0))
        actual_lines = int(module_context.get("source_lines", 0))
        actual_exports = int(module_context.get("export_count", module_context.get("estimated_exports", 0)))
        actual_classes = int(module_context.get("class_count", 0))
        actual_interfaces = int(module_context.get("interface_count", 0))
        doc_role = module_context.get("doc_role", "module")
        doc_profile = "overview" if doc_role == "overview" else "module-complete"
        return {
            "module_type": module_context.get("module_type", "module"),
            "doc_role": doc_role,
            "doc_profile": doc_profile,
            "actual_source_files": actual_files,
            "actual_source_lines": actual_lines,
            "actual_export_count": actual_exports,
            "actual_class_count": actual_classes,
            "actual_interface_count": actual_interfaces,
            "focus_source_files": actual_files,
            "focus_source_lines": actual_lines,
            "focus_export_count": actual_exports,
            "focus_class_count": actual_classes,
            "focus_interface_count": actual_interfaces,
            "source_files": actual_files,
            "source_lines": actual_lines,
            "export_count": actual_exports,
        }

    return {
        "module_type": "module",
        "doc_role": "module",
        "doc_profile": "module-complete",
        "actual_source_files": 0,
        "actual_source_lines": 0,
        "actual_export_count": 0,
        "actual_class_count": 0,
        "actual_interface_count": 0,
        "focus_source_files": 0,
        "focus_source_lines": 0,
        "focus_export_count": 0,
        "focus_class_count": 0,
        "focus_interface_count": 0,
        "source_files": 0,
        "source_lines": 0,
        "export_count": 0,
    }


def calculate_expected_metrics(doc_type: str, source_context: Dict[str, Any]) -> Dict[str, Any]:
    source_lines = int(source_context.get("actual_source_lines", source_context.get("source_lines", 0)))
    source_files = int(source_context.get("actual_source_files", source_context.get("source_files", 0)))
    export_count = int(source_context.get("actual_export_count", source_context.get("export_count", 0)))
    module_type = str(source_context.get("module_type", "module"))
    doc_role = str(source_context.get("doc_role", "module"))
    doc_profile = str(source_context.get("doc_profile", "overview" if doc_role == "overview" else "module-complete"))
    role_weight = ROLE_WEIGHTS.get(module_type, 2)

    if doc_type == "architecture":
        return {
            "min_lines": max(180, min(240, int(source_lines * 0.01) or 180)),
            "min_sections": 6,
            "min_diagrams": max(3, min(4, math.ceil(max(source_files, 1) / 320) + 1)),
            "min_examples": 1,
            "requires_source_tracing": True,
            "min_coverage_ratio": 0.005,
            "required_diagram_types": ["sequenceDiagram"],
        }
    if doc_type in INDEX_DOCS:
        return {
            "min_lines": 80 if doc_type != "getting-started" else 100,
            "min_sections": 4,
            "min_diagrams": 1,
            "min_examples": 1 if doc_type == "getting-started" else 0,
            "requires_source_tracing": False,
            "min_coverage_ratio": 0.0,
            "required_diagram_types": [],
        }
    if doc_type == "api" and doc_profile == "api-complete":
        return {
            "min_lines": max(220, min(260, int(source_lines * 0.04 + export_count * 0.25) if source_lines or export_count else 220)),
            "min_sections": max(7, role_weight + 4),
            "min_diagrams": max(2, min(3, math.ceil(max(source_files, 1) / 20) + 1)),
            "min_examples": max(4, min(6, math.ceil(export_count * 0.025) or 4)),
            "requires_source_tracing": True,
            "min_coverage_ratio": 0.12,
            "required_diagram_types": ["sequenceDiagram", "classDiagram"],
        }

    if doc_role == "overview" or doc_profile == "overview":
        return {
            "min_lines": max(180, min(240, int(source_lines * 0.02 + export_count * 0.15) if source_lines or export_count else 180)),
            "min_sections": max(7, role_weight + 4),
            "min_diagrams": max(2, min(3, math.ceil(max(source_files, 1) / 40) + 1)),
            "min_examples": max(3, min(6, math.ceil(export_count * 0.03) or 3)),
            "requires_source_tracing": doc_type in REQUIRED_SOURCE_DOCS,
            "min_coverage_ratio": 0.005,
            "required_diagram_types": ["sequenceDiagram"],
        }

    if doc_profile == "topic":
        return {
            "min_lines": 120,
            "min_sections": 6,
            "min_diagrams": 1,
            "min_examples": 1,
            "requires_source_tracing": doc_type in REQUIRED_SOURCE_DOCS,
            "min_coverage_ratio": 0.0,
            "required_diagram_types": [],
        }

    return {
        "min_lines": max(150, int(source_lines * 0.3 + export_count * 15) if source_lines or export_count else 150),
        "min_sections": 6 + role_weight,
        "min_diagrams": max(1, math.ceil(max(source_files, 1) / 5)),
        "min_examples": max(2, math.ceil(export_count * 0.5) or 2),
        "requires_source_tracing": doc_type in REQUIRED_SOURCE_DOCS,
        "min_coverage_ratio": 0.1,
        "required_diagram_types": ["sequenceDiagram", "classDiagram"],
    }


def calculate_scores(metrics: QualityMetrics) -> Tuple[float, float, float]:
    expected = metrics.expected_metrics
    min_examples = int(expected.get("min_examples", 0))
    content_ratios = {
        "lines": metrics.line_count / max(expected.get("min_lines", 1), 1),
        "examples": 1.0 if min_examples <= 0 else metrics.code_example_count / max(min_examples, 1),
        "diagrams": metrics.diagram_count / max(expected.get("min_diagrams", 1), 1),
        "sections": metrics.section_count / max(expected.get("min_sections", 1), 1),
    }
    content_score = (
        min(content_ratios["lines"], 1.5) * 0.3
        + min(content_ratios["examples"], 1.5) * 0.3
        + min(content_ratios["diagrams"], 1.5) * 0.2
        + min(content_ratios["sections"], 1.5) * 0.2
    )

    actual_lines = int(metrics.source_context.get("actual_source_lines", metrics.source_context.get("source_lines", 0)))
    focus_lines = int(metrics.source_context.get("focus_source_lines", metrics.source_context.get("source_lines", 0)))
    min_coverage = float(expected.get("min_coverage_ratio", 0.0))
    raw_coverage = 1.0 if actual_lines <= 0 else focus_lines / max(actual_lines, 1)
    if min_coverage <= 0:
        coverage_score = 1.0
    else:
        coverage_score = min(raw_coverage / min_coverage, 1.25)

    traceability_signals = 0.0
    if expected.get("requires_source_tracing"):
        if metrics.has_source_tracing:
            traceability_signals += 0.45
    else:
        traceability_signals += 0.45
    if metrics.has_related_docs:
        traceability_signals += 0.2
    if metrics.cross_link_count > 0:
        traceability_signals += 0.2
    if metrics.mermaid_issues == 0:
        traceability_signals += 0.15
    traceability_score = min(traceability_signals, 1.0)

    return round(content_score, 3), round(coverage_score, 3), round(traceability_score, 3)


def professional_threshold(metrics: QualityMetrics) -> float:
    """
    Complete docs keep a stricter professional bar. Overview/topic docs are
    expected to be concise and can graduate at a slightly lower ratio.
    """
    if metrics.doc_profile in {"module-complete", "api-complete"}:
        return 1.15
    return 1.05


def analyze_document(file_path: str, source_context: Optional[Dict[str, Any]] = None) -> QualityMetrics:
    path = Path(file_path)
    metrics = QualityMetrics(file_path=file_path, doc_type=classify_doc_type(path))

    try:
        raw_content = path.read_text(encoding="utf-8")
    except Exception as exc:
        metrics.fatal_issues.append(f"无法读取文件: {exc}")
        return metrics

    frontmatter, content = parse_frontmatter(raw_content)
    metrics.source_context = source_context or {}
    metrics.doc_profile = str(
        (source_context or {}).get("doc_profile")
        or frontmatter.get("doc_profile")
        or ("overview" if (source_context or {}).get("doc_role") == "overview" else "module-complete")
    )
    metrics.expected_metrics = calculate_expected_metrics(metrics.doc_type, {**(source_context or {}), "doc_profile": metrics.doc_profile})

    lines = content.splitlines()
    metrics.line_count = len(lines)
    metrics.section_count = len(re.findall(r"^##\s+", content, re.MULTILINE))
    metrics.subsection_count = len(re.findall(r"^###\s+", content, re.MULTILINE))
    metrics.diagram_count = len(re.findall(r"```mermaid[\s\S]*?```", content))
    metrics.class_diagram_count = len(re.findall(r"\bclassDiagram\b", content))
    metrics.sequence_diagram_count = len(re.findall(r"\bsequenceDiagram\b", content))
    metrics.state_diagram_count = len(re.findall(r"\bstateDiagram(?:-v2)?\b", content))
    metrics.code_example_count = len(re.findall(r"```(?!mermaid)[\s\S]*?```", content))
    metrics.table_count = count_tables(content)
    metrics.cross_link_count = len(re.findall(r"\[[^\]]+\]\((?!https?://)[^)]+\.md(?:#[^)]+)?\)", content))
    metrics.has_related_docs = bool(re.search(r"相关文档|related docs", content, re.IGNORECASE))

    source_link_count, has_source_tracing, source_link_issues = evaluate_source_links(content)
    metrics.source_link_count = source_link_count
    metrics.has_source_tracing = has_source_tracing

    lower_content = content.lower()
    metrics.has_best_practices = bool(re.search(r"最佳实践|best practices?", lower_content))
    metrics.has_performance = bool(re.search(r"性能优化|性能考量|performance", lower_content))
    metrics.has_troubleshooting = bool(re.search(r"错误处理|调试|故障排除|troubleshoot|debug", lower_content))

    template_issues = check_template_completeness(content)
    mermaid_issues = validate_mermaid_blocks(content)
    metrics.has_unreplaced_templates = bool(template_issues)
    metrics.mermaid_issues = len(mermaid_issues)
    metrics.fatal_issues.extend(template_issues)
    metrics.fatal_issues.extend(source_link_issues)
    metrics.fatal_issues.extend(mermaid_issues)

    expected = metrics.expected_metrics
    if expected.get("requires_source_tracing") and not metrics.has_source_tracing:
        metrics.fatal_issues.append("缺少有效源码追溯链接")

    required_diagram_types = expected.get("required_diagram_types", []) or []
    for diagram_type in required_diagram_types:
        if diagram_type == "classDiagram" and metrics.class_diagram_count <= 0:
            metrics.fatal_issues.append("缺少必需图表: classDiagram")
        if diagram_type == "sequenceDiagram" and metrics.sequence_diagram_count <= 0:
            metrics.fatal_issues.append("缺少必需图表: sequenceDiagram")
        if diagram_type == "stateDiagram" and metrics.state_diagram_count <= 0:
            metrics.fatal_issues.append("缺少必需图表: stateDiagram")

    actual_class_count = int((source_context or {}).get("actual_class_count", 0))
    actual_interface_count = int((source_context or {}).get("actual_interface_count", 0))
    if metrics.doc_profile in {"module-complete", "api-complete"} and (actual_class_count > 0 or actual_interface_count > 0):
        if metrics.class_diagram_count <= 0:
            metrics.fatal_issues.append("完整文档缺少 classDiagram（检测到 class/interface）")

    if metrics.line_count < expected["min_lines"]:
        metrics.warning_issues.append(f"行数不足: {metrics.line_count}/{expected['min_lines']}")
    if metrics.section_count < expected["min_sections"]:
        metrics.warning_issues.append(f"章节数不足: {metrics.section_count}/{expected['min_sections']}")
    if metrics.diagram_count < expected["min_diagrams"]:
        metrics.warning_issues.append(f"图表数不足: {metrics.diagram_count}/{expected['min_diagrams']}")
    if metrics.code_example_count < expected["min_examples"]:
        metrics.warning_issues.append(f"代码示例不足: {metrics.code_example_count}/{expected['min_examples']}")
    actual_lines = int((source_context or {}).get("actual_source_lines", (source_context or {}).get("source_lines", 0)))
    focus_lines = int((source_context or {}).get("focus_source_lines", (source_context or {}).get("source_lines", 0)))
    min_coverage_ratio = float(expected.get("min_coverage_ratio", 0.0))
    if actual_lines > 0 and min_coverage_ratio > 0:
        coverage_ratio = focus_lines / max(actual_lines, 1)
        if coverage_ratio < min_coverage_ratio:
            metrics.warning_issues.append(f"覆盖率不足: {coverage_ratio:.3f}/{min_coverage_ratio:.3f}")
            if metrics.doc_profile in {"module-complete", "api-complete"} and coverage_ratio < min_coverage_ratio * 0.5:
                metrics.fatal_issues.append("完整文档覆盖率严重不足")
    if metrics.cross_link_count < 1 and metrics.doc_type not in INDEX_DOCS:
        metrics.warning_issues.append("缺少交叉链接")
    if metrics.doc_type in {"module", "domain", "architecture"} and not metrics.has_related_docs:
        metrics.warning_issues.append("缺少“相关文档”章节")

    if metrics.doc_type in {"module", "domain", "architecture"}:
        module_type = str((source_context or {}).get("module_type", "module"))
        if ROLE_WEIGHTS.get(module_type, 2) >= 3:
            if not metrics.has_best_practices:
                metrics.warning_issues.append("缺少“最佳实践”章节")
            if not metrics.has_performance:
                metrics.warning_issues.append("缺少“性能优化”章节")
            if not metrics.has_troubleshooting:
                metrics.warning_issues.append("缺少“错误处理”章节")

    metrics.content_score, metrics.coverage_score, metrics.traceability_score = calculate_scores(metrics)
    weighted_total = metrics.content_score * 0.5 + metrics.coverage_score * 0.3 + metrics.traceability_score * 0.2
    metrics.score_ratio = round(weighted_total, 3)
    if metrics.fatal_issues:
        metrics.quality_level = "basic"
    elif metrics.score_ratio >= professional_threshold(metrics):
        metrics.quality_level = "professional"
    elif metrics.score_ratio >= 0.8:
        metrics.quality_level = "standard"
    else:
        metrics.quality_level = "basic"

    return metrics


def check_wiki_quality(wiki_path: str) -> QualityReport:
    report = QualityReport(wiki_path=wiki_path, check_time=datetime.now().isoformat())
    wiki_dir = Path(wiki_path) / "wiki"
    if not wiki_dir.exists():
        report.summary_issues.append(f"Wiki 目录不存在: {wiki_dir}")
        return report

    structure = load_structure(wiki_path)

    for md_file in sorted(wiki_dir.rglob("*.md")):
        try:
            raw_content = md_file.read_text(encoding="utf-8")
        except OSError:
            raw_content = ""
        frontmatter, _ = parse_frontmatter(raw_content)
        source_context = build_source_context(md_file, wiki_path, structure, frontmatter)
        metrics = analyze_document(str(md_file), source_context=source_context)
        report.docs.append(metrics)
        report.total_docs += 1

        if metrics.quality_level == "professional":
            report.professional_count += 1
        elif metrics.quality_level == "standard":
            report.standard_count += 1
        else:
            report.basic_count += 1

    return report


def print_report(report: QualityReport, verbose: bool = False) -> int:
    print("\n" + "=" * 60)
    print("Mini-Wiki 文档质量检查报告")
    print("=" * 60)
    print(f"Wiki 路径: {report.wiki_path}")
    print(f"检查时间: {report.check_time}")
    print()

    print("## 总体统计\n")
    print("| 指标 | 数值 |")
    print("|------|------|")
    print(f"| 文档总数 | {report.total_docs} |")
    print(f"| Professional | {report.professional_count} |")
    print(f"| Standard | {report.standard_count} |")
    print(f"| Basic | {report.basic_count} |")
    print()

    if report.docs:
        print("## 文档概览\n")
        print("| 文档 | 类型 | 评级 | 达标率 | Fatal | Warning |")
        print("|------|------|------|--------|-------|---------|")
        for doc in report.docs:
            rel_path = os.path.basename(doc.file_path)
            print(
                f"| {rel_path} | {doc.doc_type} | {doc.quality_level} | "
                f"{doc.score_ratio * 100:.1f}% | {len(doc.fatal_issues)} | {len(doc.warning_issues)} |"
            )
        print()

    if verbose:
        print("## 详细问题\n")
        for doc in report.docs:
            if not doc.issues:
                continue
            print(f"### {Path(doc.file_path).name} [{doc.quality_level}]")
            for issue in doc.fatal_issues:
                print(f"- Fatal: {issue}")
            for issue in doc.warning_issues:
                print(f"- Warning: {issue}")
            print()

    print("## 改进建议\n")
    if report.basic_count:
        print(f"- 优先修复 {report.basic_count} 个 Basic 文档的 fatal 问题。")
    if any(doc.warning_issues for doc in report.docs):
        print("- 根据动态期望值补齐章节、图表和代码示例。")
    if any(not doc.has_source_tracing for doc in report.docs if doc.expected_metrics.get("requires_source_tracing")):
        print("- 为模块文档和架构文档补充相对路径或 GitHub blob 源码链接。")
    print()

    if report.basic_count > 0 or any(doc.issues for doc in report.docs):
        return 1
    return 0


def save_report_json(report: QualityReport, output_path: str) -> None:
    payload = {
        "wiki_path": report.wiki_path,
        "check_time": report.check_time,
        "summary": {
            "total": report.total_docs,
            "professional": report.professional_count,
            "standard": report.standard_count,
            "basic": report.basic_count,
        },
        "docs": [],
    }

    for doc in report.docs:
        payload["docs"].append(
            {
                "file": doc.file_path,
                "doc_type": doc.doc_type,
                "doc_profile": doc.doc_profile,
                "quality_level": doc.quality_level,
                "score_ratio": doc.score_ratio,
                "scores": {
                    "content": doc.content_score,
                    "coverage": doc.coverage_score,
                    "traceability": doc.traceability_score,
                },
                "expected_metrics": doc.expected_metrics,
                "source_context": doc.source_context,
                "metrics": {
                    "lines": doc.line_count,
                    "sections": doc.section_count,
                    "subsections": doc.subsection_count,
                    "diagrams": doc.diagram_count,
                    "class_diagrams": doc.class_diagram_count,
                    "sequence_diagrams": doc.sequence_diagram_count,
                    "state_diagrams": doc.state_diagram_count,
                    "code_examples": doc.code_example_count,
                    "tables": doc.table_count,
                    "cross_links": doc.cross_link_count,
                    "source_links": doc.source_link_count,
                },
                "fatal_issues": doc.fatal_issues,
                "warning_issues": doc.warning_issues,
            }
        )

    Path(output_path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"报告已保存到: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Mini-Wiki 文档质量门禁")
    parser.add_argument("wiki_path", nargs="?", default=".mini-wiki", help="Wiki 目录路径")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细问题列表")
    parser.add_argument("--json", metavar="FILE", help="将报告保存为 JSON 文件")
    args = parser.parse_args()

    wiki_path = args.wiki_path
    if not os.path.exists(wiki_path):
        print(f"路径不存在: {wiki_path}")
        return 1

    report = check_wiki_quality(wiki_path)
    exit_code = print_report(report, verbose=args.verbose)

    if args.json:
        save_report_json(report, args.json)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
