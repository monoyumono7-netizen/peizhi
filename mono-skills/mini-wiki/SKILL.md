---
name: mini-wiki
description: |
  Automatically generate **professional-grade** structured project Wiki from documentation, code, design files, and images.

  Use when:
  - User requests "generate wiki", "create docs", "create documentation"
  - User requests "update wiki", "rebuild wiki"
  - User requests "list plugins", "install plugin", "manage plugins"
  - Project needs automated documentation generation

  Features:
  - Smart project structure and tech stack analysis
  - **Deep code analysis** with semantic understanding
  - **Mermaid diagrams** for architecture, data flow, dependencies
  - **Cross-linked documentation** network
  - Incremental updates (only changed files)
  - Code blocks link to source files
  - Multi-language support (zh/en)
  - **Plugin system for extensions**

  For Chinese instructions, see references/SKILL.zh.md
---

# Wiki Generator

生成**专业级**结构化项目 Wiki 到 `.mini-wiki/` 目录。

> **核心原则**：文档必须 **详细、结构化、有图表、相互关联**，达到企业级技术文档标准。

---

## 质量标准（精要）

> 📖 完整标准见 [quality-standards.md](references/quality-standards.md)

**质量基于模块复杂度动态计算**：

| 指标 | 计算公式 |
|------|----------|
| 文档行数 | `max(150, source_lines × 0.3 + export_count × 15)` |
| 代码示例 | `max(2, export_count × 0.5)` |
| 图表数量 | `max(1, ceil(file_count / 5))` |
| 章节数 | `6 + module_role_weight`（core +4, util +2, config +1） |

**每个文档必须包含**：
- 层级标题（H2/H3/H4）+ 表格 + Mermaid 图表 + 交叉链接
- **源码引用**（使用相对路径）：`[filename.ts L1-L50](../../../src/path/to/file.ts)`
- 核心类/接口的 **classDiagram**
- **"相关文档"** 章节

**图表类型映射**：架构→`flowchart TB`，数据流→`sequenceDiagram`，状态→`stateDiagram-v2`，类→`classDiagram`，依赖→`flowchart LR`

**Mermaid 规范**：节点 ID 只用字母数字下划线，中文标签必须双引号包裹，每个图表必须有类型声明。

---

## 输出结构

**按业务领域分层组织，而非扁平目录**：

```
.mini-wiki/
├── config.yaml
├── meta.json
├── cache/
├── wiki/
│   ├── index.md                    # 项目首页
│   ├── architecture.md             # 系统架构
│   ├── getting-started.md          # 快速开始
│   ├── doc-map.md                  # 文档关系图
│   ├── <业务领域>/                  # 自动检测的业务领域
│   │   ├── _index.md               # 领域概述
│   │   └── <子模块>.md             # 模块文档
│   └── api/                        # API 参考
└── i18n/                           # 多语言支持
```

**领域自动检测**：分析代码关键词和目录结构，自动归类到业务领域。首次生成时向用户展示领域划分方案供确认。

> 📖 领域关键词映射和回退策略见 [quality-standards.md](references/quality-standards.md#业务领域自动检测)

---

## 插件系统

**安全模型**：插件仅提供**文本指令**，用于影响分析与写作策略；**不执行任何插件代码/脚本**。

1. **加载**：读取 `plugins/_registry.yaml` 获取已启用插件
2. **读取**：读取每个插件的 `PLUGIN.md` 获取 Hooks 指引
3. **应用**：在工作流对应节点应用插件的文本指引

**Hooks**：`on_init` → `after_analyze` → `before_generate` → `after_generate` → `on_export`

**插件命令**：`list plugins` / `install plugin <source>` / `enable/disable plugin <name>`

> 📖 创建插件见 [plugin-template.md](references/plugin-template.md)

---

## 工作流

### Step 1: 初始化

检查 `.mini-wiki/` 是否存在：
- **不存在**：运行 `scripts/init_wiki.py` 创建目录结构
- **存在**：读取 `config.yaml` 和缓存

### Step 2: 插件发现

读取 `plugins/_registry.yaml`，对每个已启用插件读取 `PLUGIN.md` 并注册 Hooks。

### Step 3: 项目分析

运行 `scripts/analyze_project.py` 或手动分析：
1. 识别技术栈（package.json, Cargo.toml, go.mod 等）
2. 发现入口文件和模块结构（深度扫描 src/ 下所有目录）
3. 发现现有文档
4. 应用 `after_analyze` 插件指引

### Step 4: 深度代码分析

**必须读取源码文件**，理解代码语义：
- 函数目的、参数、返回值、副作用
- 类层次和关系
- 数据流和状态管理
- 错误处理模式和设计模式

> 📖 分析提示词模板见 [prompts.md](references/prompts.md#代码深度分析)

### Step 5: 变更检测

运行 `scripts/detect_changes.py` 对比文件校验和，识别新增/修改/删除。

### Step 6: 内容生成

应用 `before_generate` 插件指引，按以下模板生成：

| 文档 | 模板来源 | 关键要求 |
|------|----------|----------|
| `index.md` | [templates.md#首页](references/templates.md#首页模板) | 项目简介 + 架构预览图 + 导航表 |
| `architecture.md` | [templates.md#架构](references/templates.md#架构文档模板) | 系统架构图 + 技术栈表 + 数据流图 |
| `getting-started.md` | [templates.md#快速开始](references/templates.md#快速开始模板) | 前置条件 + 安装 + 第一个示例 |
| `doc-map.md` | [templates.md#索引](references/templates.md#文档索引模板) | 关系图 + 阅读路径 + 完整索引 |
| 模块文档 | [templates.md#模块](references/templates.md#模块文档模板) | 动态章节数（6-16） |
| API 文档 | [templates.md#API](references/templates.md#api-参考模板) | 签名 + 参数表 + 3 示例 |

> 📖 详细生成提示词见 [prompts.md](references/prompts.md)

应用 `after_generate` 插件指引。

### Step 7: 源码链接

为代码块添加源码相对路径链接：
```markdown
### `functionName` [`📄`](../../../src/path/to/file.ts)
```

可通过 `config.yaml` 的 `linking.source_link_style` 选择链接格式：`relative`（默认）/ `github_url`

### Step 8: 保存

- 写入 `.mini-wiki/wiki/`
- 更新 `cache/checksums.json`
- 更新 `meta.json`

---

## 大型项目渐进式扫描

当模块 > 10 或文件 > 50 或代码 > 10,000 行时启用。

**核心策略**：每批 1-2 个模块，每批后运行质量检查，用户确认后继续。

> 📖 完整策略见 [progressive-scanning.md](references/progressive-scanning.md)

---

## 文档升级

检测旧版本/低质量文档并升级。支持三种策略：全量刷新 / 渐进式升级 / 选择性升级。

**用户命令**：`检查 wiki 质量` / `升级 wiki` / `刷新全部 wiki` / `继续升级`

> 📖 完整策略见 [upgrade-strategy.md](references/upgrade-strategy.md)

---

## 脚本参考

| 脚本 | 用途 |
|------|------|
| `scripts/init_wiki.py <path>` | 初始化 .mini-wiki 目录 |
| `scripts/analyze_project.py <path>` | 分析项目结构（支持深度扫描） |
| `scripts/detect_changes.py <path>` | 检测文件变更 |
| `scripts/generate_diagram.py <wiki-dir>` | 生成 Mermaid 图表 |
| `scripts/extract_docs.py <file>` | 提取代码注释 |
| `scripts/generate_toc.py <wiki-dir>` | 生成目录 |
| `scripts/check_quality.py <wiki-dir>` | 检查文档质量（支持动态复杂度分析） |
| `scripts/plugin_manager.py <cmd>` | 管理插件 |

---

## 配置

`.mini-wiki/config.yaml`：

```yaml
generation:
  language: zh              # zh / en / both
  detail_level: detailed    # minimal / standard / detailed
  include_diagrams: true
  include_examples: true
  min_sections: 10

linking:
  source_link_style: relative  # relative / github_url
  auto_cross_links: true
  generate_doc_map: true

progressive:
  enabled: auto             # auto / always / never
  batch_size: 1
  quality_check: true

upgrade:
  auto_detect: true
  backup_before_upgrade: true
  preserve_user_content: true

exclude:
  - node_modules
  - dist
  - "*.test.ts"
```

---

## References 索引

| 文档 | 说明 |
|------|------|
| [quality-standards.md](references/quality-standards.md) | 完整质量标准、动态公式、领域检测 |
| [progressive-scanning.md](references/progressive-scanning.md) | 大型项目渐进式扫描策略 |
| [upgrade-strategy.md](references/upgrade-strategy.md) | 文档升级刷新策略 |
| [prompts.md](references/prompts.md) | AI 生成提示词模板 |
| [templates.md](references/templates.md) | Wiki 页面 Markdown 模板 |
| [plugin-template.md](references/plugin-template.md) | 插件开发模板 |
