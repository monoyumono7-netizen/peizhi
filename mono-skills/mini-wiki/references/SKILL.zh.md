# Wiki 自动生成技能（中文版）

本文件为 SKILL.md 的中文参考。主技能文件为英文版 `SKILL.md`，本文档提供中文说明。

> **核心原则**：文档必须 **详细、结构化、有图表、相互关联**，达到企业级技术文档标准。

---

## 质量标准（精要）

> 📖 完整标准见 [quality-standards.md](quality-standards.md)

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

> 📖 领域关键词映射和回退策略见 [quality-standards.md](quality-standards.md#业务领域自动检测)

---

## 插件系统

**安全模型**：插件仅提供**文本指令**，影响分析与写作策略；**不执行任何插件代码/脚本**。

1. **加载**：读取 `plugins/_registry.yaml`
2. **读取**：读取每个插件的 `PLUGIN.md`
3. **应用**：在工作流对应节点应用文本指引

**Hooks**：`on_init` → `after_analyze` → `before_generate` → `after_generate` → `on_export`

**插件命令**：`列出插件` / `安装插件 <来源>` / `启用/禁用插件 <名称>`

---

## 工作流

### 第 1 步：初始化

检查 `.mini-wiki/` 是否存在。不存在则运行 `scripts/init_wiki.py`，存在则读取配置和缓存。

### 第 2 步：插件发现

读取 `plugins/_registry.yaml`，加载已启用插件的 `PLUGIN.md`。

### 第 3 步：项目分析

运行 `scripts/analyze_project.py` 或手动分析：识别技术栈、发现入口文件和模块结构、发现现有文档。

### 第 4 步：深度代码分析

**必须读取源码文件**，理解代码语义（函数目的、类关系、数据流、设计模式）。

> 📖 分析提示词模板见 [prompts.md](prompts.md#代码深度分析)

### 第 5 步：变更检测

运行 `scripts/detect_changes.py` 对比文件校验和。

### 第 6 步：内容生成

按模板生成各类文档。

| 文档 | 模板来源 | 关键要求 |
|------|----------|----------|
| `index.md` | [templates.md#首页](templates.md#首页模板) | 项目简介 + 架构预览图 + 导航表 |
| `architecture.md` | [templates.md#架构](templates.md#架构文档模板) | 系统架构图 + 技术栈表 + 数据流图 |
| `getting-started.md` | [templates.md#快速开始](templates.md#快速开始模板) | 前置条件 + 安装 + 示例 |
| `doc-map.md` | [templates.md#索引](templates.md#文档索引模板) | 关系图 + 阅读路径 + 完整索引 |
| 模块文档 | [templates.md#模块](templates.md#模块文档模板) | 动态章节数（6-16） |
| API 文档 | [templates.md#API](templates.md#api-参考模板) | 签名 + 参数表 + 3 示例 |

### 第 7 步：源码链接

使用相对路径格式：`### functionName [📄](../../../src/path/to/file.ts)`

### 第 8 步：保存

写入 `.mini-wiki/wiki/`，更新缓存和元数据。

---

## 大型项目渐进式扫描

当模块 > 10 或文件 > 50 或代码 > 10,000 行时启用。每批 1-2 个模块，每批后质量检查。

> 📖 完整策略见 [progressive-scanning.md](progressive-scanning.md)

---

## 文档升级

检测旧版本/低质量文档并升级。三种策略：全量刷新 / 渐进式升级 / 选择性升级。

**用户命令**：`检查 wiki 质量` / `升级 wiki` / `刷新全部 wiki` / `继续升级`

> 📖 完整策略见 [upgrade-strategy.md](upgrade-strategy.md)

---

## 脚本参考

| 脚本 | 用途 |
|------|------|
| `scripts/init_wiki.py <path>` | 初始化 .mini-wiki 目录 |
| `scripts/analyze_project.py <path>` | 分析项目结构 |
| `scripts/detect_changes.py <path>` | 检测文件变更 |
| `scripts/check_quality.py <wiki-dir>` | 检查文档质量 |
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
  enabled: auto
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
| [quality-standards.md](quality-standards.md) | 完整质量标准、动态公式、领域检测 |
| [progressive-scanning.md](progressive-scanning.md) | 大型项目渐进式扫描策略 |
| [upgrade-strategy.md](upgrade-strategy.md) | 文档升级刷新策略 |
| [prompts.md](prompts.md) | AI 生成提示词模板 |
| [templates.md](templates.md) | Wiki 页面 Markdown 模板 |
| [plugin-template.md](plugin-template.md) | 插件开发模板 |
