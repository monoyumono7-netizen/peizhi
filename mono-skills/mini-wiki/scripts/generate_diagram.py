#!/usr/bin/env python3
"""
Mermaid diagram generator for Mini-Wiki.

The generator consumes structure.json produced by analyze_project.py and keeps
all generated diagrams Mermaid-safe.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def safe_id(value: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", value)
    return sanitized or "node"


def trim_modules(modules: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    return sorted(modules, key=lambda item: item.get("importance", 0), reverse=True)[:limit]


def render_subgraph(name: str, title: str, modules: List[Dict[str, Any]]) -> List[str]:
    if not modules:
        return []
    lines = [f'    subgraph {name}["{title}"]']
    for module in modules:
        node_id = safe_id(module.get("slug", module.get("name", "module")))
        label = module.get("slug", module.get("name", "module"))
        lines.append(f'        {node_id}["{label}"]')
    lines.append("    end")
    return lines


def generate_architecture_diagram(structure: Dict[str, Any]) -> str:
    modules = structure.get("modules", [])
    ui_modules = trim_modules([module for module in modules if module.get("module_type") in {"ui", "routing", "hooks"}], 6)
    workflow_modules = trim_modules([module for module in modules if module.get("module_type") in {"workflow", "state", "event"}], 6)
    service_modules = trim_modules([module for module in modules if module.get("module_type") in {"api", "ai", "media"}], 6)
    shared_modules = trim_modules([module for module in modules if module.get("module_type") in {"utility", "types", "config"}], 6)
    native_modules = trim_modules([module for module in modules if "stage/" in module.get("path", "") or "kiwi" in module.get("path", "")], 4)

    lines = ["```mermaid", "flowchart TB"]
    sections = [
        ("UI", "界面层", ui_modules),
        ("Workflow", "工作流层", workflow_modules),
        ("Services", "服务层", service_modules),
        ("Shared", "共享层", shared_modules),
        ("Native", "Native/WASM 层", native_modules),
    ]

    active_sections = [name for name, title, section_modules in sections if section_modules]
    for name, title, section_modules in sections:
        lines.extend(render_subgraph(name, title, section_modules))
        if section_modules:
            lines.append("")

    if not active_sections:
        lines.extend(
            [
                '    App["应用"]',
                '    Logic["业务逻辑"]',
                '    Utils["工具模块"]',
                "    App --> Logic",
                "    Logic --> Utils",
            ]
        )
    else:
        if "UI" in active_sections and "Workflow" in active_sections:
            lines.append("    UI --> Workflow")
        if "Workflow" in active_sections and "Services" in active_sections:
            lines.append("    Workflow --> Services")
        if "Services" in active_sections and "Shared" in active_sections:
            lines.append("    Services --> Shared")
        elif "Workflow" in active_sections and "Shared" in active_sections:
            lines.append("    Workflow --> Shared")
        if "Workflow" in active_sections and "Native" in active_sections:
            lines.append("    Workflow --> Native")

    lines.append("```")
    return "\n".join(lines)


def generate_module_dependency_diagram(module_name: str, dependencies: Dict[str, List[str]]) -> str:
    lines = ["```mermaid", "flowchart LR"]
    root_id = safe_id(module_name)
    lines.append(f'    {root_id}["{module_name}"]')

    for index, dependency in enumerate(dependencies.get("internal", [])[:8]):
        dep_label = Path(dependency).stem or dependency
        dep_id = f"{safe_id(dep_label)}_{index}"
        lines.append(f'    {root_id} --> {dep_id}["{dep_label}"]')

    externals = dependencies.get("external", [])[:5]
    if externals:
        lines.append(f'    {root_id} --> ext_{root_id}["外部依赖"]')
        for index, dependency in enumerate(externals):
            dep_id = f"ext_{safe_id(dependency)}_{index}"
            lines.append(f'    ext_{root_id} --> {dep_id}["{dependency}"]')

    lines.append("```")
    return "\n".join(lines)


def generate_file_tree_diagram(structure: Dict[str, Any]) -> str:
    modules = trim_modules(structure.get("modules", []), 12)
    lines = ["```mermaid", "mindmap", '  root(("项目结构"))']
    for module in modules:
        lines.append(f'    "{module.get("slug", module.get("name", "module"))}"')
        lines.append(f'      "{module.get("source_files", 0)} files / {module.get("source_lines", 0)} lines"')
    lines.append("```")
    return "\n".join(lines)


def generate_data_flow_diagram(entry_points: List[str], modules: List[Dict[str, Any]]) -> str:
    lines = ["```mermaid", "sequenceDiagram", "    participant User as 用户", "    participant Entry as 入口"]
    chain = trim_modules(
        [module for module in modules if module.get("module_type") in {"routing", "workflow", "api", "ai", "state"}],
        4,
    )
    for module in chain:
        alias = safe_id(module.get("slug", module.get("name", "module")))
        label = module.get("slug", module.get("name", "module"))
        lines.append(f"    participant {alias} as {label}")

    lines.append("")
    lines.append("    User->>Entry: 打开页面 / 触发操作")

    previous = "Entry"
    for module in chain:
        alias = safe_id(module.get("slug", module.get("name", "module")))
        lines.append(f"    {previous}->>{alias}: 调用")
        previous = alias

    lines.append(f"    {previous}-->>User: 返回结果")
    lines.append("```")
    return "\n".join(lines)


def generate_class_diagram(classes: List[Dict[str, Any]]) -> str:
    lines = ["```mermaid", "classDiagram"]
    for cls in classes[:10]:
        class_name = cls.get("name", "Unknown")
        alias = safe_id(class_name)
        lines.append(f"    class {alias} {{")
        for prop in cls.get("properties", [])[:5]:
            lines.append(f"        +{prop}")
        for method in cls.get("methods", [])[:5]:
            lines.append(f"        +{method}()")
        lines.append("    }")
    lines.append("```")
    return "\n".join(lines)


def load_structure(wiki_dir: str) -> Optional[Dict[str, Any]]:
    structure_path = Path(wiki_dir) / "cache" / "structure.json"
    if not structure_path.exists():
        return None
    try:
        return json.loads(structure_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python generate_diagram.py <.mini-wiki目录>")
        raise SystemExit(1)

    wiki_dir = sys.argv[1]
    structure = load_structure(wiki_dir)
    if not structure:
        print("未找到项目结构数据")
        raise SystemExit(1)

    print("=== 架构图 ===")
    print(generate_architecture_diagram(structure))
    print()
    print("=== 目录结构图 ===")
    print(generate_file_tree_diagram(structure))
