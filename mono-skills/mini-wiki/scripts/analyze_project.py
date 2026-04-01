#!/usr/bin/env python3
"""
项目结构分析脚本 v3.0
扫描项目目录，识别项目类型、模块结构和文档位置
支持深度模块发现、嵌套模块检测和重要性评分
输出适配 .mini-wiki 目录结构
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone

# 忽略的目录
IGNORE_DIRS = {
    'node_modules', '.git', 'dist', 'build', '__pycache__',
    '.next', '.nuxt', 'coverage', '.nyc_output', 'vendor',
    'venv', '.venv', 'env', '.env', 'eggs', '.eggs',
    '.tox', '.cache', '.pytest_cache', '.mypy_cache',
    '.mini-wiki', '.agent'
}

# 忽略的文件
IGNORE_FILES = {
    '.DS_Store', 'Thumbs.db', '.gitignore', '.gitattributes',
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
    'poetry.lock', 'Pipfile.lock', 'composer.lock'
}

# 项目类型检测规则
PROJECT_INDICATORS = {
    'nodejs': ['package.json'],
    'typescript': ['tsconfig.json', 'tsconfig.*.json'],
    'python': ['requirements.txt', 'pyproject.toml', 'setup.py', 'Pipfile'],
    'go': ['go.mod', 'go.sum'],
    'rust': ['Cargo.toml'],
    'java': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
    'ruby': ['Gemfile'],
    'php': ['composer.json'],
    'dotnet': ['*.csproj', '*.fsproj', '*.sln'],
    'react': ['package.json'],  # 需进一步检查依赖
    'vue': ['vue.config.js', 'vite.config.ts', 'nuxt.config.ts'],
    'nextjs': ['next.config.js', 'next.config.mjs', 'next.config.ts'],
}

# 代码文件扩展名
CODE_EXTENSIONS = {
    '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs',
    '.py', '.pyi',
    '.go',
    '.rs',
    '.java', '.kt', '.scala',
    '.rb',
    '.php',
    '.cs', '.fs',
    '.vue', '.svelte', '.astro'
}



def detect_package_manager(root_path: Path) -> List[str]:
    """检测包管理器"""
    managers = []
    if (root_path / 'package-lock.json').exists():
        managers.append('npm')
    if (root_path / 'yarn.lock').exists():
        managers.append('yarn')
    if (root_path / 'pnpm-lock.yaml').exists():
        managers.append('pnpm')
    if (root_path / 'bun.lockb').exists():
        managers.append('bun')
    return managers


def detect_monorepo_tools(root_path: Path) -> List[str]:
    """检测 Monorepo 工具"""
    tools = []
    
    # workspace configs
    if (root_path / 'pnpm-workspace.yaml').exists():
        tools.append('pnpm-workspaces')
        if 'monorepo' not in tools: tools.append('monorepo')
        
    if (root_path / 'lerna.json').exists():
        tools.append('lerna')
        if 'monorepo' not in tools: tools.append('monorepo')
        
    if (root_path / 'turbo.json').exists():
        tools.append('turborepo')
        if 'monorepo' not in tools: tools.append('monorepo')
        
    # check package.json for workspaces
    pkg_path = root_path / 'package.json'
    if pkg_path.exists():
        try:
            with open(pkg_path, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
                if 'workspaces' in pkg:
                    tools.append('npm-workspaces') # or yarn/bun workspaces, generic term
                    if 'monorepo' not in tools: tools.append('monorepo')
        except Exception:
            pass
            
    return tools


def detect_project_types(root_path: Path) -> List[str]:
    """检测项目类型"""
    types = []
    
    # 基础文件检测
    for project_type, indicators in PROJECT_INDICATORS.items():
        for indicator in indicators:
            if '*' in indicator:
                if list(root_path.glob(indicator)):
                    types.append(project_type)
                    break
            elif (root_path / indicator).exists():
                types.append(project_type)
                break
    
    # 检测包管理器
    types.extend(detect_package_manager(root_path))
    
    # 检测 Monorepo
    types.extend(detect_monorepo_tools(root_path))
    
    # Python 深度检测 (pyproject.toml)
    pyproject_path = root_path / 'pyproject.toml'
    if pyproject_path.exists():
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                tomllib = None
        
        if tomllib:
            try:
                with open(pyproject_path, 'rb') as f:
                    pyproject = tomllib.load(f)
                    
                    # Detect build system
                    build_backend = pyproject.get('build-system', {}).get('build-backend', '')
                    if 'poetry' in build_backend:
                        types.append('poetry')
                    elif 'pdm' in build_backend:
                        types.append('pdm')
                    elif 'setuptools' in build_backend:
                        types.append('setuptools')
                    elif 'flit' in build_backend:
                        types.append('flit')
                        
                    # Detect specific python frameworks in dependencies
                    # Poetry
                    deps = pyproject.get('tool', {}).get('poetry', {}).get('dependencies', {})
                    # Standard project.dependencies
                    deps_std = pyproject.get('project', {}).get('dependencies', [])
                    
                    all_deps = set()
                    if isinstance(deps, dict):
                        all_deps.update(deps.keys())
                    if isinstance(deps_std, list):
                        # Simple parsing for "package>=1.0"
                        import re
                        for d in deps_std:
                            match = re.match(r'^([a-zA-Z0-9_-]+)', d)
                            if match:
                                all_deps.add(match.group(1))
                                
                    if 'fastapi' in all_deps: types.append('fastapi')
                    if 'django' in all_deps: types.append('django')
                    if 'flask' in all_deps: types.append('flask')
                    
            except Exception:
                pass

    # Node.js 深度检测 (package.json)
    if 'nodejs' in types or (root_path / 'package.json').exists():
        pkg_path = root_path / 'package.json'
        if pkg_path.exists():
            try:
                with open(pkg_path, 'r', encoding='utf-8') as f:
                    pkg = json.load(f)
                    deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                    
                    if 'react' in deps and 'react' not in types:
                        types.append('react')
                    if 'vue' in deps and 'vue' not in types:
                        types.append('vue')
                    if 'next' in deps and 'nextjs' not in types:
                        types.append('nextjs')
                    if 'nuxt' in deps or '@nuxt/core' in deps:
                        types.append('nuxt')
            except Exception:
                pass

    # Rust 深度检测 (Cargo.toml)
    cargo_path = root_path / 'Cargo.toml'
    if cargo_path.exists():
        try:
            with open(cargo_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Simple TOML parsing for dependencies
                # Note: A real TOML parser would be better but requires external lib
                if 'actix-web' in content: types.append('actix-web')
                if 'axum' in content: types.append('axum')
                if 'tokio' in content: types.append('tokio')
                if 'tauri' in content: types.append('tauri')
                if 'rocket' in content: types.append('rocket')
        except Exception:
            pass
            
    # Go 深度检测 (go.mod)
    go_mod_path = root_path / 'go.mod'
    if go_mod_path.exists():
        try:
            with open(go_mod_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'github.com/gin-gonic/gin' in content: types.append('gin')
                if 'github.com/labstack/echo' in content: types.append('echo')
                if 'github.com/gofiber/fiber' in content: types.append('fiber')
                if 'gorm.io/gorm' in content: types.append('gorm')
        except Exception:
            pass
    
    return list(set(types))



def find_entry_points(root_path: Path, project_types: List[str]) -> List[str]:
    """识别入口文件"""
    entries = []
    
    # 常见入口文件
    common_entries = [
        'src/index.ts', 'src/index.tsx', 'src/index.js',
        'src/main.ts', 'src/main.tsx', 'src/main.js',
        'src/App.tsx', 'src/App.vue',
        'app/page.tsx', 'pages/index.tsx', 'pages/index.vue',
        'main.py', 'app.py', 'src/main.py',
        'cmd/main.go', 'main.go',
        'src/main.rs', 'src/lib.rs',
    ]
    
    for entry in common_entries:
        if (root_path / entry).exists():
            entries.append(entry)
    
    return entries


def count_source_lines(dir_path: Path, exclude_dirs: Set[str] = None) -> int:
    """统计目录下所有源代码文件的总行数"""
    if exclude_dirs is None:
        exclude_dirs = IGNORE_DIRS
    total = 0
    try:
        for f in dir_path.rglob('*'):
            if (f.is_file()
                    and f.suffix in CODE_EXTENSIONS
                    and not any(p in f.parts for p in exclude_dirs)):
                try:
                    total += sum(1 for _ in open(f, 'r', encoding='utf-8', errors='ignore'))
                except OSError:
                    pass
    except OSError:
        pass
    return total


def detect_module_boundaries(dir_path: Path) -> Dict[str, Any]:
    """
    检测模块边界信息：是否有 index 入口文件、导出数量、被引用次数估算

    Returns:
        {
            'has_index': bool,
            'index_file': str | None,
            'estimated_exports': int,
        }
    """
    index_candidates = ['index.ts', 'index.tsx', 'index.js', 'index.jsx']
    has_index = False
    index_file = None
    estimated_exports = 0

    for candidate in index_candidates:
        idx_path = dir_path / candidate
        if idx_path.exists():
            has_index = True
            index_file = candidate
            # 统计导出数量：粗略计算 export 关键字出现次数
            try:
                content = idx_path.read_text(encoding='utf-8', errors='ignore')
                estimated_exports = content.count('export ')
            except OSError:
                pass
            break

    return {
        'has_index': has_index,
        'index_file': index_file,
        'estimated_exports': estimated_exports,
    }


def calculate_module_importance(
    module: Dict[str, Any],
    entry_points: List[str] = None,
) -> float:
    """
    计算模块重要性得分

    评分维度：
      - entry_point_bonus: 模块路径匹配入口文件 → +5
      - dependency_count (estimated_exports × 4): 导出越多被依赖可能性越高
      - file_count_normalized (min(files, 50) / 50 × 2): 文件数归一化
      - has_docs: 模块目录下有 README → +3
      - recency: 保留字段，暂给 1 分
    """
    if entry_points is None:
        entry_points = []

    score = 0.0

    # 入口文件加分
    mod_path = module.get('path', '')
    for ep in entry_points:
        if ep.startswith(mod_path + '/') or ep.startswith(mod_path + os.sep):
            score += 5
            break

    # 导出数量 × 4（上限 40）
    exports = module.get('estimated_exports', 0)
    score += min(exports, 10) * 4

    # 文件数归一化 × 2
    files = module.get('files', 0)
    score += (min(files, 50) / 50) * 2

    # 有文档加分
    if module.get('has_docs', False):
        score += 3

    # 基础 recency 分
    score += 1

    module['importance'] = round(score, 2)
    return score


def discover_modules_deep(
    root_path: Path,
    exclude_dirs: Set[str] = None,
    nested_file_threshold: int = 10,
    entry_points: List[str] = None,
) -> List[Dict[str, Any]]:
    """
    深度模块发现：扫描标准目录及其所有子目录，支持嵌套模块

    策略：
    1. 扫描标准顶层目录（src, lib, packages, apps, modules）
    2. 对每个顶层目录，扫描所有直接子目录作为模块
    3. 嵌套模块：如果某子目录下的子目录文件数 >= nested_file_threshold，
       也将其作为独立模块
    4. 为每个模块计算重要性得分并排序
    """
    if exclude_dirs is None:
        exclude_dirs = IGNORE_DIRS
    if entry_points is None:
        entry_points = []

    modules: List[Dict[str, Any]] = []
    seen_paths: Set[str] = set()
    src_dirs = ['src', 'lib', 'packages', 'apps', 'modules']

    def _count_code_files(dir_path: Path) -> int:
        return sum(
            1 for f in dir_path.rglob('*')
            if f.is_file()
            and f.suffix in CODE_EXTENSIONS
            and not any(p in f.parts for p in exclude_dirs)
        )

    def _make_module(dir_path: Path) -> Optional[Dict[str, Any]]:
        rel = str(dir_path.relative_to(root_path))
        if rel in seen_paths:
            return None
        file_count = _count_code_files(dir_path)
        if file_count == 0:
            return None

        seen_paths.add(rel)
        boundary = detect_module_boundaries(dir_path)
        has_docs = (dir_path / 'README.md').exists() or (dir_path / 'readme.md').exists()

        mod = {
            'name': dir_path.name,
            'path': rel,
            'files': file_count,
            'type': categorize_module(dir_path.name),
            'has_index': boundary['has_index'],
            'index_file': boundary['index_file'],
            'estimated_exports': boundary['estimated_exports'],
            'has_docs': has_docs,
        }
        calculate_module_importance(mod, entry_points)
        return mod

    # 第一层：扫描标准顶层目录下的所有直接子目录
    for src_dir in src_dirs:
        src_path = root_path / src_dir
        if not src_path.exists() or not src_path.is_dir():
            continue

        for item in sorted(src_path.iterdir()):
            if not item.is_dir() or item.name in exclude_dirs or item.name.startswith('.'):
                continue

            mod = _make_module(item)
            if mod:
                modules.append(mod)

            # 第二层：嵌套模块发现
            for sub_item in sorted(item.iterdir()):
                if not sub_item.is_dir() or sub_item.name in exclude_dirs or sub_item.name.startswith('.'):
                    continue
                sub_file_count = _count_code_files(sub_item)
                if sub_file_count >= nested_file_threshold:
                    sub_mod = _make_module(sub_item)
                    if sub_mod:
                        # 标记为嵌套模块，名称使用 parent/child 格式
                        sub_mod['name'] = f"{item.name}/{sub_item.name}"
                        sub_mod['nested'] = True
                        modules.append(sub_mod)

    # 按重要性降序排序
    modules.sort(key=lambda m: m.get('importance', 0), reverse=True)
    return modules


def discover_modules(root_path: Path, exclude_dirs: Set[str] = None) -> List[Dict[str, Any]]:
    """发现项目模块"""
    if exclude_dirs is None:
        exclude_dirs = IGNORE_DIRS
    
    modules = []
    src_dirs = ['src', 'lib', 'packages', 'apps', 'modules']
    
    for src_dir in src_dirs:
        src_path = root_path / src_dir
        if not src_path.exists():
            continue
        
        for item in src_path.iterdir():
            if item.is_dir() and item.name not in exclude_dirs:
                # 统计文件数
                file_count = sum(1 for f in item.rglob('*') 
                               if f.is_file() and f.suffix in CODE_EXTENSIONS
                               and not any(p in f.parts for p in exclude_dirs))
                
                if file_count > 0:
                    modules.append({
                        'name': item.name,
                        'path': str(item.relative_to(root_path)),
                        'files': file_count,
                        'type': categorize_module(item.name)
                    })
    
    # 始终尝试深度发现以获取更好的模块拆分
    # 当有大型模块（>100 文件）时，深度发现能将其拆分为子模块
    has_large_modules = any(m.get('files', 0) > 100 for m in modules)
    if len(modules) < 5 or has_large_modules:
        deep_modules = discover_modules_deep(root_path, exclude_dirs)
        if len(deep_modules) > len(modules):
            return deep_modules

    # 如果没有找到明确的模块，尝试根目录下的主要目录
    if not modules:
        for item in root_path.iterdir():
            if item.is_dir() and item.name not in exclude_dirs and not item.name.startswith('.'):
                file_count = sum(1 for f in item.rglob('*')
                               if f.is_file() and f.suffix in CODE_EXTENSIONS)
                if file_count > 0:
                    modules.append({
                        'name': item.name,
                        'path': item.name,
                        'files': file_count,
                        'type': categorize_module(item.name)
                    })

    return modules


def categorize_module(name: str) -> str:
    """根据名称分类模块"""
    name_lower = name.lower()

    # 按优先级匹配，更具体的规则优先
    if any(k in name_lower for k in ['workflow', 'flow', 'editor', 'canvas']):
        return 'workflow'
    elif any(k in name_lower for k in ['event', 'bus', 'emitter', 'rxjs', 'observable']):
        return 'event'
    elif any(k in name_lower for k in ['store', 'state', 'slice', 'zustand', 'redux']):
        return 'state'
    elif any(k in name_lower for k in ['cloud', 'agent', 'ai', 'chat', 'llm']):
        return 'ai'
    elif any(k in name_lower for k in ['media', 'video', 'audio', 'ffmpeg', 'konva']):
        return 'media'
    elif any(k in name_lower for k in ['hook', 'hooks']):
        return 'hooks'
    elif any(k in name_lower for k in ['route', 'router', 'page']):
        return 'routing'
    elif name_lower in ('type', 'types', 'interface', 'interfaces'):
        return 'types'
    elif any(k in name_lower for k in ['component', 'ui', 'view', 'widget']):
        return 'ui'
    elif any(k in name_lower for k in ['api', 'service', 'handler']):
        return 'api'
    elif any(k in name_lower for k in ['util', 'helper', 'common', 'shared']):
        return 'utility'
    elif any(k in name_lower for k in ['core', 'lib', 'engine']):
        return 'core'
    elif any(k in name_lower for k in ['config', 'setting']):
        return 'config'
    elif any(k in name_lower for k in ['test', 'spec']):
        return 'test'
    else:
        return 'module'


def find_documentation(root_path: Path) -> List[str]:
    """发现现有文档"""
    doc_patterns = [
        'README.md', 'README.*.md', 'readme.md',
        'CHANGELOG.md', 'HISTORY.md', 'changelog.md',
        'CONTRIBUTING.md', 'ARCHITECTURE.md', 'DESIGN.md',
        'API.md', 'SECURITY.md', 'LICENSE', 'LICENSE.md',
        'docs/*.md', 'documentation/*.md'
    ]
    
    docs = []
    for pattern in doc_patterns:
        if '*' in pattern:
            docs.extend(str(p.relative_to(root_path)) for p in root_path.glob(pattern))
        elif (root_path / pattern).exists():
            docs.append(pattern)
    
    return docs


def analyze_project(project_root: str, save_to_cache: bool = True) -> Dict[str, Any]:
    """
    完整分析项目结构
    
    Args:
        project_root: 项目根目录
        save_to_cache: 是否保存到 .mini-wiki/cache/structure.json
    
    Returns:
        项目结构数据
    """
    root = Path(project_root)
    
    # 检测项目类型
    project_types = detect_project_types(root)
    
    # 发现入口文件
    entry_points = find_entry_points(root, project_types)
    
    # 发现模块
    modules = discover_modules(root)
    
    # 发现文档
    docs = find_documentation(root)
    
    # 统计代码文件
    code_files = []
    for ext in CODE_EXTENSIONS:
        for f in root.rglob(f'*{ext}'):
            if not any(p in f.parts for p in IGNORE_DIRS):
                code_files.append(str(f.relative_to(root)))
    
    result = {
        'project_name': root.name,
        'project_type': project_types,
        'entry_points': entry_points,
        'modules': modules,
        'docs_found': docs,
        'stats': {
            'total_files': len(code_files),
            'total_modules': len(modules),
            'total_docs': len(docs)
        },
        'analyzed_at': datetime.now(timezone.utc).isoformat()
    }
    
    # 保存到缓存
    if save_to_cache:
        wiki_dir = root / '.mini-wiki'
        if wiki_dir.exists():
            cache_path = wiki_dir / 'cache' / 'structure.json'
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
    
    return result


def print_analysis(result: Dict[str, Any]):
    """打印分析结果"""
    print(f"📁 项目: {result['project_name']}")
    print(f"🔧 技术栈: {', '.join(result['project_type']) or '未知'}")
    print(f"📊 统计: {result['stats']['total_files']} 个代码文件, "
          f"{result['stats']['total_modules']} 个模块, "
          f"{result['stats']['total_docs']} 个文档")
    
    if result['entry_points']:
        print(f"\n🚀 入口文件:")
        for entry in result['entry_points']:
            print(f"  - {entry}")
    
    if result['modules']:
        print(f"\n📦 模块:")
        for module in result['modules'][:20]:
            importance = module.get('importance', '')
            imp_str = f" ⭐{importance}" if importance else ''
            nested_str = ' [嵌套]' if module.get('nested') else ''
            print(f"  - {module['name']} ({module['files']} 个文件, {module['type']}){imp_str}{nested_str}")
    
    if result['docs_found']:
        print(f"\n📄 现有文档:")
        for doc in result['docs_found']:
            print(f"  - {doc}")


if __name__ == '__main__':
    import sys
    
    project_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    result = analyze_project(project_path, save_to_cache=False)
    print_analysis(result)
