#!/usr/bin/env python3
"""
Navigation generator for the v3 Mini-Wiki layout.
"""

from pathlib import Path
from typing import Dict, List
import json


def extract_title_from_markdown(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped.startswith("# "):
                    return stripped[2:].strip()
    except OSError:
        pass
    return Path(file_path).stem.replace("-", " ").replace("_", " ").title()


def collect_markdown_files(directory: Path) -> List[Path]:
    if not directory.exists():
        return []
    return sorted(path for path in directory.glob("*.md") if path.is_file())


def generate_toc(wiki_dir: str, base_url: str = "") -> str:
    wiki_path = Path(wiki_dir)
    if not wiki_path.exists():
        return "目录为空"

    toc_lines = ["# 目录\n"]

    main_docs = [
        ("index.md", "项目首页"),
        ("getting-started.md", "快速开始"),
        ("architecture.md", "系统架构总览"),
        ("doc-map.md", "阅读地图"),
    ]

    for filename, default_title in main_docs:
        file_path = wiki_path / filename
        if not file_path.exists():
            continue
        toc_lines.append(f"- [{extract_title_from_markdown(str(file_path)) or default_title}]({base_url}{filename})")

    domains = collect_markdown_files(wiki_path / "domains")
    if domains:
        toc_lines.append("\n## 领域文档\n")
        for md_file in domains:
            toc_lines.append(f"- [{extract_title_from_markdown(str(md_file))}]({base_url}domains/{md_file.name})")

    apis = collect_markdown_files(wiki_path / "api")
    if apis:
        toc_lines.append("\n## API 文档\n")
        for md_file in apis:
            toc_lines.append(f"- [{extract_title_from_markdown(str(md_file))}]({base_url}api/{md_file.name})")

    return "\n".join(toc_lines)


def generate_sidebar(wiki_dir: str) -> str:
    wiki_path = Path(wiki_dir)
    sidebar: Dict[str, List[Dict[str, str]]] = {
        "/": [
            {"text": "项目首页", "link": "/"},
            {"text": "快速开始", "link": "/getting-started"},
            {"text": "系统架构总览", "link": "/architecture"},
            {"text": "阅读地图", "link": "/doc-map"},
        ]
    }

    domains = [file for file in collect_markdown_files(wiki_path / "domains") if file.name != "_index.md"]
    if domains:
        sidebar["/domains/"] = [
            {"text": extract_title_from_markdown(str(md_file)), "link": f"/domains/{md_file.stem}"}
            for md_file in domains
        ]

    apis = collect_markdown_files(wiki_path / "api")
    if apis:
        sidebar["/api/"] = [
            {"text": extract_title_from_markdown(str(md_file)), "link": f"/api/{md_file.stem}"}
            for md_file in apis
        ]

    return json.dumps(sidebar, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python generate_toc.py <wiki目录路径>")
        raise SystemExit(1)

    print(generate_toc(sys.argv[1]))
