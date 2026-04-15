#!/usr/bin/env python3
"""
Mini-Wiki plugin manager.

Production-oriented behavior:
- Local plugin installs are always allowed.
- Remote plugin installs require explicit opt-in.
- Remote archives are host-allowlisted, size-limited, and safely extracted.
- Registry metadata preserves the original source so updates work reliably.
"""

import os
import re
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import yaml

from config_utils import load_yaml_file

DOWNLOAD_TIMEOUT_SECONDS = 20
DEFAULT_REMOTE_POLICY = {
    "allow_remote_install": False,
    "allow_http": False,
    "max_download_bytes": 25_000_000,
    "allowed_hosts": [
        "github.com",
        "codeload.github.com",
        "raw.githubusercontent.com",
    ],
}


def get_plugins_dir(project_root: str) -> Path:
    return Path(project_root) / "plugins"


def get_registry_path(project_root: str) -> Path:
    return get_plugins_dir(project_root) / "_registry.yaml"


def truthy_env(name: str) -> Optional[bool]:
    value = os.getenv(name)
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_policy(project_root: str) -> Dict[str, Any]:
    policy = dict(DEFAULT_REMOTE_POLICY)

    for candidate in (
        Path(project_root) / ".mini-wiki" / "config.yaml",
        Path(project_root) / "assets" / "config.yaml",
    ):
        config = load_yaml_file(candidate)
        plugins = config.get("plugins", {})
        if isinstance(plugins, dict):
            policy.update({key: value for key, value in plugins.items() if value is not None})

    env_allow_remote = truthy_env("MINI_WIKI_ALLOW_REMOTE_INSTALL")
    if env_allow_remote is not None:
        policy["allow_remote_install"] = env_allow_remote

    env_allow_http = truthy_env("MINI_WIKI_ALLOW_HTTP_PLUGIN_INSTALL")
    if env_allow_http is not None:
        policy["allow_http"] = env_allow_http

    env_hosts = os.getenv("MINI_WIKI_PLUGIN_ALLOWED_HOSTS")
    if env_hosts:
        policy["allowed_hosts"] = [host.strip() for host in env_hosts.split(",") if host.strip()]

    env_max_size = os.getenv("MINI_WIKI_PLUGIN_MAX_DOWNLOAD_BYTES")
    if env_max_size and env_max_size.isdigit():
        policy["max_download_bytes"] = int(env_max_size)

    return policy


def load_registry(project_root: str) -> Dict[str, Any]:
    registry_path = get_registry_path(project_root)
    if registry_path.exists():
        with open(registry_path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {"plugins": []}
    return {"plugins": []}


def save_registry(project_root: str, registry: Dict[str, Any]) -> None:
    registry_path = get_registry_path(project_root)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_path, "w", encoding="utf-8") as handle:
        yaml.dump(registry, handle, default_flow_style=False, allow_unicode=True, sort_keys=False)


def parse_plugin_manifest(plugin_path: Path) -> Optional[Dict[str, Any]]:
    manifest_path = plugin_path / "PLUGIN.md"
    if not manifest_path.exists():
        return None

    content = manifest_path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None
    try:
        manifest = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    return manifest if isinstance(manifest, dict) else None


def list_plugins(project_root: str) -> List[Dict[str, Any]]:
    plugins_dir = get_plugins_dir(project_root)
    registry = load_registry(project_root)
    plugins: List[Dict[str, Any]] = []

    if not plugins_dir.exists():
        return []

    for item in sorted(plugins_dir.iterdir()):
        if not item.is_dir() or item.name.startswith("_"):
            continue
        manifest = parse_plugin_manifest(item)
        if not manifest:
            continue
        reg_entry = next((entry for entry in registry.get("plugins", []) if entry.get("name") == manifest["name"]), None)
        plugins.append(
            {
                **manifest,
                "path": str(item),
                "enabled": reg_entry.get("enabled", True) if reg_entry else True,
                "priority": reg_entry.get("priority", 100) if reg_entry else 100,
                "source": reg_entry.get("source") if reg_entry else None,
            }
        )

    return sorted(plugins, key=lambda item: item.get("priority", 100))


def sanitize_plugin_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "-", name).strip("-").lower()
    return cleaned or "unknown-plugin"


def resolve_source_metadata(source: str) -> Dict[str, Any]:
    if re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", source):
        owner_repo = source
        return {
            "type": "github",
            "origin": owner_repo,
            "branch": "main",
            "download_url": f"https://github.com/{owner_repo}/archive/refs/heads/main.zip",
        }

    if source.startswith(("http://", "https://")):
        return {"type": "url", "origin": source, "branch": None, "download_url": source}

    return {"type": "local", "origin": source, "branch": None, "download_url": None}


def assert_remote_allowed(project_root: str, metadata: Dict[str, Any]) -> None:
    if metadata["type"] == "local":
        return

    policy = load_policy(project_root)
    if not policy.get("allow_remote_install", False):
        raise ValueError("Remote plugin install is disabled. Set MINI_WIKI_ALLOW_REMOTE_INSTALL=1 to enable it.")

    download_url = metadata.get("download_url") or metadata.get("origin")
    parsed = urlparse(download_url)
    if parsed.scheme != "https" and not policy.get("allow_http", False):
        raise ValueError("Only HTTPS plugin sources are allowed.")

    host = parsed.hostname or ""
    if host not in set(policy.get("allowed_hosts", [])):
        raise ValueError(f'Remote host "{host}" is not allowlisted for plugin installation.')


def safe_extract_archive(archive_path: Path, destination: Path, max_bytes: int) -> None:
    total_size = 0
    with zipfile.ZipFile(archive_path, "r") as archive:
        for member in archive.infolist():
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Unsafe archive member: {member.filename}")
            total_size += member.file_size
            if total_size > max_bytes:
                raise ValueError(f"Archive exceeds size limit ({max_bytes} bytes)")

        for member in archive.infolist():
            target_path = (destination / member.filename).resolve()
            if not str(target_path).startswith(str(destination.resolve())):
                raise ValueError(f"Unsafe archive extraction path: {member.filename}")
            archive.extract(member, destination)


def download_remote_archive(project_root: str, metadata: Dict[str, Any], archive_path: Path) -> None:
    assert_remote_allowed(project_root, metadata)
    policy = load_policy(project_root)
    req = urllib.request.Request(metadata["download_url"], headers={"User-Agent": "Mini-Wiki-Plugin-Manager"})

    with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response, open(archive_path, "wb") as out_file:
        declared_length = response.headers.get("Content-Length")
        max_bytes = int(policy["max_download_bytes"])
        if declared_length and int(declared_length) > max_bytes:
            raise ValueError(f"Archive exceeds allowed download size ({max_bytes} bytes)")

        downloaded = 0
        while True:
            chunk = response.read(8192)
            if not chunk:
                break
            downloaded += len(chunk)
            if downloaded > max_bytes:
                raise ValueError(f"Archive exceeds allowed download size ({max_bytes} bytes)")
            out_file.write(chunk)


def find_plugin_root(extracted_root: Path) -> Path:
    if (extracted_root / "PLUGIN.md").exists() or (extracted_root / "SKILL.md").exists():
        return extracted_root

    candidates = []
    for item in sorted(extracted_root.iterdir()):
        if item.is_dir() and ((item / "PLUGIN.md").exists() or (item / "SKILL.md").exists() or (item / "README.md").exists()):
            candidates.append(item)
    return candidates[0] if candidates else extracted_root


def stage_source(project_root: str, source: str, work_dir: Path) -> tuple[Path, Dict[str, Any]]:
    metadata = resolve_source_metadata(source)
    source_input_path = Path(source)

    if metadata["type"] == "local" and source_input_path.is_dir():
        staged_path = work_dir / "plugin-src"
        shutil.copytree(source_input_path, staged_path)
        return staged_path, metadata

    archive_path = work_dir / "plugin.zip"
    if metadata["type"] == "local":
        if not source_input_path.exists():
            raise FileNotFoundError(f"Plugin source not found: {source}")
        shutil.copy2(source_input_path, archive_path)
    else:
        download_remote_archive(project_root, metadata, archive_path)

    extract_dir = work_dir / "extract"
    extract_dir.mkdir(parents=True, exist_ok=True)
    safe_extract_archive(archive_path, extract_dir, int(load_policy(project_root)["max_download_bytes"]))
    return find_plugin_root(extract_dir), metadata


def infer_plugin_name_from_skill(skill_path: Path) -> str:
    content = skill_path.read_text(encoding="utf-8")
    match = re.search(r"^name:\s*(.+)$", content, re.MULTILINE)
    return match.group(1).strip() if match else skill_path.parent.name


def ensure_manifest(staged_path: Path) -> Dict[str, Any]:
    manifest_path = staged_path / "PLUGIN.md"
    if manifest_path.exists():
        manifest = parse_plugin_manifest(staged_path)
        if manifest:
            return manifest
        raise ValueError("PLUGIN.md frontmatter is invalid.")

    skill_path = staged_path / "SKILL.md"
    if skill_path.exists():
        target_name = infer_plugin_name_from_skill(skill_path)
        content = skill_path.read_text(encoding="utf-8")
        manifest_path.write_text(
            f"""---
name: {target_name}
type: enhancer
version: 1.0.0
description: Auto-wrapped skill from standard SKILL.md
author: unknown
requires:
  - mini-wiki >= 2.0.0
hooks:
  - after_analyze
  - before_generate
---

# {target_name}

> Auto-wrapped from SKILL.md

{content}
""",
            encoding="utf-8",
        )
        return parse_plugin_manifest(staged_path) or {"name": target_name, "type": "enhancer", "version": "1.0.0"}

    target_name = staged_path.name
    manifest_path.write_text(
        f"""---
name: {target_name}
type: enhancer
version: 1.0.0
description: Auto-wrapped generic plugin
author: unknown
requires:
  - mini-wiki >= 2.0.0
hooks:
  - after_analyze
---

# {target_name}

> Auto-wrapped from repository content.
""",
        encoding="utf-8",
    )
    return parse_plugin_manifest(staged_path) or {"name": target_name, "type": "enhancer", "version": "1.0.0"}


def install_plugin(project_root: str, source: str) -> Dict[str, Any]:
    plugins_dir = get_plugins_dir(project_root)
    plugins_dir.mkdir(parents=True, exist_ok=True)
    result = {"success": False, "message": "", "name": None}

    try:
        with tempfile.TemporaryDirectory(prefix="mini-wiki-plugin-") as temp_dir:
            staged_path, source_meta = stage_source(project_root, source, Path(temp_dir))
            manifest = ensure_manifest(staged_path)
            target_name = sanitize_plugin_name(str(manifest.get("name", "unknown-plugin")))
            target_dir = plugins_dir / target_name

            if target_dir.exists():
                shutil.rmtree(target_dir)
            shutil.copytree(staged_path, target_dir)

            registry = load_registry(project_root)
            plugins = [entry for entry in registry.get("plugins", []) if entry.get("name") != target_name]
            plugins.append(
                {
                    "name": target_name,
                    "enabled": True,
                    "priority": len(plugins) * 10 + 10,
                    "type": manifest.get("type", "enhancer"),
                    "version": manifest.get("version", "0.0.0"),
                    "source": {
                        "type": source_meta["type"],
                        "origin": source_meta["origin"],
                        "branch": source_meta.get("branch"),
                    },
                    "installed_at": datetime.now().isoformat(),
                }
            )
            registry["plugins"] = plugins
            save_registry(project_root, registry)

            result["success"] = True
            result["name"] = target_name
            result["message"] = f'Plugin "{target_name}" installed successfully'
    except Exception as exc:
        result["message"] = f"Installation failed: {exc}"

    return result


def enable_plugin(project_root: str, name: str, enabled: bool = True) -> Dict[str, Any]:
    registry = load_registry(project_root)
    plugins = registry.get("plugins", [])

    for plugin in plugins:
        if plugin.get("name") == name:
            plugin["enabled"] = enabled
            save_registry(project_root, registry)
            status = "enabled" if enabled else "disabled"
            return {"success": True, "message": f'Plugin "{name}" {status}'}

    return {"success": False, "message": f'Plugin "{name}" not found'}


def uninstall_plugin(project_root: str, name: str) -> Dict[str, Any]:
    plugins_dir = get_plugins_dir(project_root)
    plugin_path = plugins_dir / name
    if not plugin_path.exists():
        return {"success": False, "message": f'Plugin "{name}" not found'}

    shutil.rmtree(plugin_path)
    registry = load_registry(project_root)
    registry["plugins"] = [entry for entry in registry.get("plugins", []) if entry.get("name") != name]
    save_registry(project_root, registry)
    return {"success": True, "message": f'Plugin "{name}" uninstalled'}


def update_plugin(project_root: str, name: str) -> Dict[str, Any]:
    registry = load_registry(project_root)
    plugin_entry = next((entry for entry in registry.get("plugins", []) if entry.get("name") == name), None)
    if not plugin_entry:
        return {"success": False, "message": f'Plugin "{name}" not found'}

    source_meta = plugin_entry.get("source", {})
    if isinstance(source_meta, str):
        source = source_meta
    else:
        source = source_meta.get("origin")

    if not source:
        return {"success": False, "message": f'Plugin "{name}" does not have source metadata'}

    if isinstance(source_meta, dict) and source_meta.get("type") == "local":
        return {"success": False, "message": f'Plugin "{name}" is installed locally. Please update files manually.'}

    return install_plugin(project_root, source)


def print_plugins(plugins: List[Dict[str, Any]]) -> None:
    if not plugins:
        print("No plugins installed.")
        return

    print(f"{'Name':<25} {'Type':<12} {'Version':<10} {'Status':<10}")
    print("-" * 60)
    for plugin in plugins:
        status = "enabled" if plugin.get("enabled", True) else "disabled"
        print(f"{plugin.get('name', 'unknown'):<25} {plugin.get('type', '-'):<12} {plugin.get('version', '-'):<10} {status:<10}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python plugin_manager.py list [project_path]")
        print("  python plugin_manager.py install <source> [project_path]")
        print("  python plugin_manager.py update <name> [project_path]")
        print("  python plugin_manager.py enable <name> [project_path]")
        print("  python plugin_manager.py disable <name> [project_path]")
        print("  python plugin_manager.py uninstall <name> [project_path]")
        raise SystemExit(1)

    command = sys.argv[1]
    project_path = os.getcwd()
    args = sys.argv[2:]
    source = None
    target_name = None

    if command == "install":
        if args:
            source = args[0]
        if len(args) > 1 and not args[1].startswith("-"):
            project_path = args[1]
    elif command == "update":
        if args:
            target_name = args[0]
        if len(args) > 1 and not args[1].startswith("-"):
            project_path = args[1]
    elif command in {"enable", "disable", "uninstall"}:
        if args:
            target_name = args[0]
        if len(args) > 1 and not args[1].startswith("-"):
            project_path = args[1]
    elif command == "list":
        if args and not args[0].startswith("-"):
            project_path = args[0]

    print(f"Project root: {project_path}")

    if command == "list":
        print_plugins(list_plugins(project_path))
        raise SystemExit(0)
    if command == "install":
        if not source:
            print("Error: source path or URL required")
            raise SystemExit(1)
        result = install_plugin(project_path, source)
        print(result["message"])
        raise SystemExit(0 if result["success"] else 1)
    if command == "update":
        if not target_name:
            print("Error: plugin name required")
            raise SystemExit(1)
        result = update_plugin(project_path, target_name)
        print(result["message"])
        raise SystemExit(0 if result["success"] else 1)
    if command == "enable":
        if not target_name:
            print("Error: plugin name required")
            raise SystemExit(1)
        result = enable_plugin(project_path, target_name, True)
        print(result["message"])
        raise SystemExit(0 if result["success"] else 1)
    if command == "disable":
        if not target_name:
            print("Error: plugin name required")
            raise SystemExit(1)
        result = enable_plugin(project_path, target_name, False)
        print(result["message"])
        raise SystemExit(0 if result["success"] else 1)
    if command == "uninstall":
        if not target_name:
            print("Error: plugin name required")
            raise SystemExit(1)
        result = uninstall_plugin(project_path, target_name)
        print(result["message"])
        raise SystemExit(0 if result["success"] else 1)

    print(f"Unknown command: {command}")
    raise SystemExit(1)
