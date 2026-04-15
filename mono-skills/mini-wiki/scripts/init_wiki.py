#!/usr/bin/env python3
"""
Mini-Wiki bootstrapper.

The generated structure matches the v3 documentation contract and includes the
configuration keys required by the analyzer, quality gate, and future upgrade
workflow.
"""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict


def get_default_config() -> str:
    return """# Mini-Wiki configuration

generation:
  language: zh
  doc_profile: overview
  profile_name: null
  detail_level: detailed
  include_diagrams: true
  include_examples: true
  min_sections: 10
  max_file_size: 200000
  doc_frontmatter: true

linking:
  source_link_style: relative
  github_repo_url: ""
  github_ref: main
  auto_cross_links: true
  generate_doc_map: true

progressive:
  enabled: auto
  batch_size: 2
  quality_check: true
  resume_from_cache: true

upgrade:
  auto_detect: true
  backup_before_upgrade: true
  preserve_user_content: true

governance:
  require_owner: true
  owner_file: OWNERS
  review_status_default: approved
  publish_requires_approval: false
  minimum_publish_quality: professional
  block_publish_on_warnings: true
  include_quality_score: true

plugins:
  allow_remote_install: false
  allow_http: false
  max_download_bytes: 25000000
  allowed_hosts:
    - github.com
    - codeload.github.com
    - raw.githubusercontent.com

project:
  workspace_root: auto
  detect_internal_dependencies: true
  infer_domain_docs: true

exclude:
  - node_modules
  - .git
  - dist
  - build
  - coverage
  - __pycache__
  - venv
  - .venv
  - "*.test.ts"
  - "*.test.tsx"
  - "*.spec.ts"
  - "*.spec.tsx"
  - "*.bak"
"""


def get_default_meta() -> Dict[str, object]:
    return {
        "version": "3.1.0",
        "schema_version": 2,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": None,
        "files_documented": 0,
        "modules_count": 0,
        "quality_status": "draft",
        "quality_ruleset_version": None,
        "generation_signature": None,
    }


def init_mini_wiki(project_root: str, force: bool = False) -> Dict[str, object]:
    root = Path(project_root)
    wiki_dir = root / ".mini-wiki"
    result: Dict[str, object] = {"success": True, "created": [], "skipped": [], "message": ""}

    if wiki_dir.exists() and not force:
        result["success"] = False
        result["message"] = ".mini-wiki 目录已存在。使用 force=True 重新初始化。"
        return result

    if wiki_dir.exists() and force:
        config_path = wiki_dir / "config.yaml"
        if config_path.exists():
            backup_path = wiki_dir / "config.yaml.bak"
            shutil.copy(config_path, backup_path)
            result["skipped"].append("config.yaml (已备份)")

    directories = [
        ".mini-wiki",
        ".mini-wiki/cache",
        ".mini-wiki/wiki",
        ".mini-wiki/wiki/api",
        ".mini-wiki/wiki/assets",
        ".mini-wiki/i18n",
        ".mini-wiki/i18n/en",
        ".mini-wiki/i18n/zh",
    ]

    for relative_dir in directories:
        directory = root / relative_dir
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            result["created"].append(relative_dir)

    config_path = wiki_dir / "config.yaml"
    if force or not config_path.exists():
        config_path.write_text(get_default_config(), encoding="utf-8")
        result["created"].append("config.yaml")

    meta_path = wiki_dir / "meta.json"
    if force or not meta_path.exists():
        meta_path.write_text(json.dumps(get_default_meta(), indent=2, ensure_ascii=False), encoding="utf-8")
        result["created"].append("meta.json")

    cache_files = {
        "cache/checksums.json": {},
        "cache/structure.json": {
            "project_name": root.name,
            "project_root": str(root.resolve()),
            "workspace_root": None,
            "project_type": [],
            "entry_points": [],
            "modules": [],
            "docs_found": [],
            "docs_catalog": [],
            "internal_dependencies": [],
            "workspace_packages": {},
            "stats": {
                "total_files": 0,
                "total_modules": 0,
                "total_docs": 0,
                "source_lines": 0,
            },
        },
    }

    for relative_path, payload in cache_files.items():
        cache_path = wiki_dir / relative_path
        if force or not cache_path.exists():
            cache_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            result["created"].append(relative_path)

    gitignore_path = wiki_dir / ".gitignore"
    if force or not gitignore_path.exists():
        gitignore_path.write_text("cache/\n*.bak\nquality-report.json\n", encoding="utf-8")
        result["created"].append(".gitignore")

    result["message"] = f"成功初始化 .mini-wiki 目录，创建了 {len(result['created'])} 个文件/目录"
    return result


def print_result(result: Dict[str, object]) -> None:
    if result["success"]:
        print("✅", result["message"])
        if result["created"]:
            print("\n创建的文件/目录:")
            for item in result["created"]:
                print(f"  + {item}")
        if result["skipped"]:
            print("\n跳过的文件:")
            for item in result["skipped"]:
                print(f"  - {item}")
    else:
        print("❌", result["message"])


if __name__ == "__main__":
    import sys

    project_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    force = "--force" in sys.argv
    print_result(init_mini_wiki(project_path, force=force))
