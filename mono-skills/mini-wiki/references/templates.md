# Wiki 页面模板

本文件包含生成**专业级** Wiki 各页面的 Markdown 模板。

> **核心原则**：每个模板都包含 **详细内容区域、Mermaid 图表、交叉链接**，确保生成的文档达到企业级标准。
> **生产约束**：完整文档（`module-complete` / `api-complete`）应包含 frontmatter，至少声明 `doc_type`、`module_type`、`source_paths`、`owner`、`review_status`、`generated_at`、`quality_score`。`overview` / `topic` 可更轻量，不等于完整模块文档。

## Frontmatter 规范

```yaml
---
doc_type: module-complete
module_type: workflow
source_paths:
  - src/components/workflow
owner: team-webflow
review_status: draft
generated_at: 2026-04-02T00:00:00Z
quality_score: pending
---
```

## 文档类型与审阅状态

| `doc_type` | 定义 | 说明 |
|------------|------|------|
| `overview` | 概览文档 | 入口、导览、总览，不视为完整模块文档 |
| `module-complete` | 完整模块文档 | 覆盖职责、结构、图表、源码追溯与关联文档 |
| `topic` | 主题文档 | 聚焦单个主题或局部流程，不要求完整模块覆盖 |
| `api-complete` | 完整 API 文档 | 覆盖完整 API 签名、参数、返回值与示例 |

| `review_status` | 含义 | 说明 |
|-----------------|------|------|
| `draft` | 草稿 | 初始状态，可继续编辑 |
| `reviewed` | 已审阅 | 内容与来源已检查 |
| `approved` | 已批准 | 满足发布前置条件 |
| `published` | 已发布 | 对外可见，进入稳定维护 |

审阅状态流转：`draft -> reviewed -> approved -> published`

`overview` / `topic` 不是完整模块文档，不能按 `module-complete` 的覆盖率要求来判定质量。

## 目录

1. [首页模板](#首页模板)
2. [架构文档模板](#架构文档模板)
3. [模块文档模板](#模块文档模板)
4. [API 参考模板](#api-参考模板)
5. [快速开始模板](#快速开始模板)
6. [文档索引模板](#文档索引模板)
7. [配置模板](#配置模板)

---

## 首页模板

```markdown
# {{ PROJECT_NAME }}

[![技术栈](https://img.shields.io/badge/Tech-{{ TECH_STACK }}-blue)](#技术栈一览)
[![版本](https://img.shields.io/badge/Version-{{ VERSION }}-green)](#)
[![模块数](https://img.shields.io/badge/Modules-{{ TOTAL_MODULES }}-orange)](#核心模块)
[![文档](https://img.shields.io/badge/Docs-Complete-brightgreen)](#文档导航)

> {{ PROJECT_DESCRIPTION }}

---

## � 项目简介

{{ PROJECT_INTRODUCTION }}

本项目主要解决以下问题：
- **问题 1**：详细描述...
- **问题 2**：详细描述...
- **问题 3**：详细描述...

适用场景：
- 场景 1 描述
- 场景 2 描述

---

## 🏗 架构预览

> 详细架构请查看 [架构文档](architecture.md)

\`\`\`mermaid
flowchart TB
    subgraph Core["核心层"]
        {{ CORE_MODULES }}
    end
    
    subgraph Support["支撑层"]
        {{ SUPPORT_MODULES }}
    end
    
    Core --> Support
    
    click Core "architecture.md" "查看架构详情"
\`\`\`

---

## �📚 文档导航

| 类别 | 文档 | 描述 | 适合人群 |
|------|------|------|----------|
| 🚀 入门 | [快速开始](getting-started.md) | 5 分钟上手指南 | 新用户 |
| 🏗 架构 | [架构概览](architecture.md) | 系统设计和技术选型 | 架构师、开发者 |
| 📦 模块 | [模块文档](modules/_index.md) | 各模块详细说明 | 开发者 |
| 📖 API | [API 参考](api/_index.md) | 完整接口文档 | 开发者 |
| 🗺 索引 | [文档地图](doc-map.md) | 文档关系与阅读路径 | 所有人 |

---

## ✨ 核心特性

| 特性 | 描述 | 相关模块 |
|------|------|----------|
| 🚀 **{{ FEATURE_1_NAME }}** | {{ FEATURE_1_DESC }} | [`module1`](modules/module1.md) |
| 📦 **{{ FEATURE_2_NAME }}** | {{ FEATURE_2_DESC }} | [`module2`](modules/module2.md) |
| 🔧 **{{ FEATURE_3_NAME }}** | {{ FEATURE_3_DESC }} | [`module3`](modules/module3.md) |
| 📊 **{{ FEATURE_4_NAME }}** | {{ FEATURE_4_DESC }} | [`module4`](modules/module4.md) |

---

## 🚀 快速开始

### 安装

\`\`\`bash
{{ INSTALL_COMMAND }}
\`\`\`

### 基础用法

\`\`\`{{ LANG }}
{{ QUICK_EXAMPLE }}
\`\`\`

### 预期输出

\`\`\`
{{ EXPECTED_OUTPUT }}
\`\`\`

> 📖 更多示例请查看 [快速开始指南](getting-started.md)

---

## 🏗 项目结构

\`\`\`
{{ PROJECT_NAME }}/
├── {{ DIR_1 }}/              # {{ DIR_1_DESC }}
│   ├── {{ SUBDIR_1 }}/       # {{ SUBDIR_1_DESC }}
│   └── {{ SUBDIR_2 }}/       # {{ SUBDIR_2_DESC }}
├── {{ DIR_2 }}/              # {{ DIR_2_DESC }}
├── {{ DIR_3 }}/              # {{ DIR_3_DESC }}
└── {{ CONFIG_FILES }}        # 配置文件
\`\`\`

---

## 📦 核心模块

| 模块 | 职责 | 文件数 | 文档 | API |
|------|------|--------|------|-----|
| [{{ MODULE_1 }}](modules/{{ MODULE_1 }}.md) | {{ MODULE_1_DESC }} | {{ MODULE_1_FILES }} | [📖](modules/{{ MODULE_1 }}.md) | [📄](api/{{ MODULE_1 }}.md) |
| [{{ MODULE_2 }}](modules/{{ MODULE_2 }}.md) | {{ MODULE_2_DESC }} | {{ MODULE_2_FILES }} | [📖](modules/{{ MODULE_2 }}.md) | [📄](api/{{ MODULE_2 }}.md) |
| [{{ MODULE_3 }}](modules/{{ MODULE_3 }}.md) | {{ MODULE_3_DESC }} | {{ MODULE_3_FILES }} | [📖](modules/{{ MODULE_3 }}.md) | [📄](api/{{ MODULE_3 }}.md) |

---

## 🔧 技术栈一览

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| {{ TECH_CATEGORY_1 }} | {{ TECH_1 }} | {{ VERSION_1 }} | {{ PURPOSE_1 }} |
| {{ TECH_CATEGORY_2 }} | {{ TECH_2 }} | {{ VERSION_2 }} | {{ PURPOSE_2 }} |
| {{ TECH_CATEGORY_3 }} | {{ TECH_3 }} | {{ VERSION_3 }} | {{ PURPOSE_3 }} |

---

## 📊 项目统计

| 指标 | 数值 | 说明 |
|------|------|------|
| 📁 代码文件 | {{ TOTAL_FILES }} | 不含测试和配置 |
| 📦 模块数 | {{ TOTAL_MODULES }} | 核心功能模块 |
| 📄 文档页 | {{ TOTAL_DOCS }} | Wiki 文档数 |
| 🔧 公开 API | {{ TOTAL_APIS }} | 导出的接口数 |

---

## 🤝 贡献与支持

- � [贡献指南](CONTRIBUTING.md)
- 🐛 [问题反馈]({{ ISSUES_URL }})
- 💬 [讨论区]({{ DISCUSSIONS_URL }})

---

## 📄 相关链接

- [更新日志](CHANGELOG.md)
- [许可证](LICENSE)
- {{ EXTERNAL_LINKS }}

---

*由 [Mini-Wiki v{{ MINI_WIKI_VERSION }}](https://github.com/trsoliu/mini-wiki) 自动生成 | {{ GENERATED_AT }}*
```

---

## 架构文档模板

```markdown
# 系统架构

> {{ PROJECT_NAME }} 的技术架构全面概览

---

## 📋 执行摘要

### 项目定位

{{ PROJECT_POSITIONING }}

### 技术选型概述

{{ TECH_OVERVIEW }}

### 架构风格

本项目采用 **{{ ARCHITECTURE_STYLE }}** 架构，主要特点：
- {{ ARCH_FEATURE_1 }}
- {{ ARCH_FEATURE_2 }}
- {{ ARCH_FEATURE_3 }}

---

## 🏗 系统架构图

\`\`\`mermaid
flowchart TB
    subgraph Presentation["🖥 表现层"]
        direction LR
        UI["UI 组件<br/>用户界面"]
        Pages["页面<br/>路由入口"]
        Hooks["Hooks<br/>状态逻辑"]
    end
    
    subgraph Business["⚙️ 业务层"]
        direction LR
        Services["服务层<br/>业务逻辑"]
        Models["模型层<br/>数据结构"]
        Validators["验证层<br/>数据校验"]
    end
    
    subgraph Data["💾 数据层"]
        direction LR
        API["API 客户端<br/>外部通信"]
        Store["状态管理<br/>全局状态"]
        Cache["缓存层<br/>性能优化"]
    end
    
    subgraph Infrastructure["🔧 基础设施"]
        direction LR
        Utils["工具函数"]
        Config["配置管理"]
        Logger["日志系统"]
    end
    
    Presentation --> Business
    Business --> Data
    Data --> Infrastructure
    Business --> Infrastructure
    
    style Presentation fill:#e1f5fe
    style Business fill:#fff3e0
    style Data fill:#e8f5e9
    style Infrastructure fill:#f3e5f5
\`\`\`

---

## 🔧 技术栈详解

### 核心技术

| 类别 | 技术 | 版本 | 选型原因 | 官方文档 |
|------|------|------|----------|----------|
| {{ CATEGORY_1 }} | {{ TECH_1 }} | {{ VERSION_1 }} | {{ REASON_1 }} | [文档]({{ DOC_URL_1 }}) |
| {{ CATEGORY_2 }} | {{ TECH_2 }} | {{ VERSION_2 }} | {{ REASON_2 }} | [文档]({{ DOC_URL_2 }}) |
| {{ CATEGORY_3 }} | {{ TECH_3 }} | {{ VERSION_3 }} | {{ REASON_3 }} | [文档]({{ DOC_URL_3 }}) |

### 开发工具

| 工具 | 用途 | 配置文件 |
|------|------|----------|
| {{ TOOL_1 }} | {{ TOOL_1_PURPOSE }} | `{{ TOOL_1_CONFIG }}` |
| {{ TOOL_2 }} | {{ TOOL_2_PURPOSE }} | `{{ TOOL_2_CONFIG }}` |

---

## 📦 模块划分详解

### 模块依赖关系图

\`\`\`mermaid
flowchart LR
    subgraph Core["核心模块"]
        A["{{ MODULE_A }}"]
        B["{{ MODULE_B }}"]
    end
    
    subgraph Features["功能模块"]
        C["{{ MODULE_C }}"]
        D["{{ MODULE_D }}"]
    end
    
    subgraph Utils["工具模块"]
        E["{{ MODULE_E }}"]
    end
    
    A --> E
    B --> E
    C --> A
    C --> B
    D --> B
    
    style A fill:#ffcdd2
    style B fill:#ffcdd2
    style C fill:#c8e6c9
    style D fill:#c8e6c9
    style E fill:#fff9c4
\`\`\`

### 模块说明

#### {{ MODULE_A }} - 核心模块

| 属性 | 说明 |
|------|------|
| **路径** | `{{ MODULE_A_PATH }}` |
| **职责** | {{ MODULE_A_RESPONSIBILITY }} |
| **核心接口** | `{{ MODULE_A_INTERFACES }}` |
| **依赖** | {{ MODULE_A_DEPS }} |
| **文档** | [模块文档](modules/{{ MODULE_A }}.md) \| [API](api/{{ MODULE_A }}.md) |

{{ MODULE_A_DETAILED_DESC }}

#### {{ MODULE_B }} - 核心模块

| 属性 | 说明 |
|------|------|
| **路径** | `{{ MODULE_B_PATH }}` |
| **职责** | {{ MODULE_B_RESPONSIBILITY }} |
| **核心接口** | `{{ MODULE_B_INTERFACES }}` |
| **依赖** | {{ MODULE_B_DEPS }} |
| **文档** | [模块文档](modules/{{ MODULE_B }}.md) \| [API](api/{{ MODULE_B }}.md) |

{{ MODULE_B_DETAILED_DESC }}

---

## 🔄 数据流

### 典型请求流程

\`\`\`mermaid
sequenceDiagram
    autonumber
    participant User as 👤 用户
    participant UI as 🖥 UI组件
    participant Service as ⚙️ 服务层
    participant API as 🌐 API客户端
    participant Server as 🖧 后端服务
    
    User->>UI: 1. 触发操作
    UI->>Service: 2. 调用服务方法
    Service->>Service: 3. 数据验证
    Service->>API: 4. 发起请求
    API->>Server: 5. HTTP 请求
    Server-->>API: 6. 返回数据
    API-->>Service: 7. 解析响应
    Service-->>UI: 8. 更新状态
    UI-->>User: 9. 渲染结果
\`\`\`

### 状态管理流程

\`\`\`mermaid
stateDiagram-v2
    [*] --> Idle: 初始化
    Idle --> Loading: 发起请求
    Loading --> Success: 请求成功
    Loading --> Error: 请求失败
    Success --> Idle: 重置
    Error --> Idle: 重试/重置
    Error --> Loading: 重试
\`\`\`

---

## 📁 目录结构说明

\`\`\`
{{ PROJECT_NAME }}/
├── src/                          # 源代码目录
│   ├── components/               # UI 组件
│   │   ├── common/               # 通用组件（Button, Input 等）
│   │   ├── layout/               # 布局组件（Header, Footer 等）
│   │   └── features/             # 功能组件（业务相关）
│   ├── services/                 # 业务服务层
│   │   ├── api/                  # API 调用封装
│   │   └── business/             # 业务逻辑
│   ├── hooks/                    # 自定义 Hooks
│   ├── store/                    # 状态管理
│   ├── utils/                    # 工具函数
│   ├── types/                    # TypeScript 类型定义
│   └── config/                   # 配置文件
├── tests/                        # 测试文件
├── docs/                         # 文档
└── scripts/                      # 构建脚本
\`\`\`

---

## 🎨 设计原则与模式

### 采用的设计模式

| 模式 | 应用场景 | 相关模块 |
|------|----------|----------|
| **{{ PATTERN_1 }}** | {{ PATTERN_1_USAGE }} | {{ PATTERN_1_MODULES }} |
| **{{ PATTERN_2 }}** | {{ PATTERN_2_USAGE }} | {{ PATTERN_2_MODULES }} |
| **{{ PATTERN_3 }}** | {{ PATTERN_3_USAGE }} | {{ PATTERN_3_MODULES }} |

### 代码组织原则

1. **{{ PRINCIPLE_1_NAME }}**
   - {{ PRINCIPLE_1_DESC }}
   
2. **{{ PRINCIPLE_2_NAME }}**
   - {{ PRINCIPLE_2_DESC }}

3. **{{ PRINCIPLE_3_NAME }}**
   - {{ PRINCIPLE_3_DESC }}

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 文件名 | {{ FILE_NAMING }} | `{{ FILE_EXAMPLE }}` |
| 组件名 | {{ COMPONENT_NAMING }} | `{{ COMPONENT_EXAMPLE }}` |
| 函数名 | {{ FUNCTION_NAMING }} | `{{ FUNCTION_EXAMPLE }}` |
| 变量名 | {{ VARIABLE_NAMING }} | `{{ VARIABLE_EXAMPLE }}` |

---

## 🔌 扩展指南

### 添加新模块

1. 在 `src/` 下创建模块目录
2. 实现核心功能
3. 导出公开接口
4. 添加单元测试
5. 更新文档

### 添加新功能

\`\`\`mermaid
flowchart LR
    A["需求分析"] --> B["设计接口"]
    B --> C["实现功能"]
    C --> D["编写测试"]
    D --> E["更新文档"]
    E --> F["代码审查"]
    F --> G["合并发布"]
\`\`\`

---

## 📄 相关文档

| 文档 | 描述 |
|------|------|
| [← 首页](index.md) | 项目概览 |
| [模块文档](modules/_index.md) | 各模块详细说明 |
| [API 参考](api/_index.md) | 接口文档 |
| [快速开始](getting-started.md) | 上手指南 |

---

*由 [Mini-Wiki v{{ MINI_WIKI_VERSION }}](https://github.com/trsoliu/mini-wiki) 自动生成 | {{ GENERATED_AT }}*
```

---

## 模块文档模板

适用于 `module-complete`。`overview` / `topic` 只用于入口或聚焦说明，不替代完整模块文档。

```markdown
# {{ MODULE_NAME }}

> {{ MODULE_SHORT_DESC }}

---

## 📋 模块概览

### 简介

{{ MODULE_INTRODUCTION_PARA_1 }}

{{ MODULE_INTRODUCTION_PARA_2 }}

### 核心价值

- **{{ VALUE_1 }}**：{{ VALUE_1_DESC }}
- **{{ VALUE_2 }}**：{{ VALUE_2_DESC }}
- **{{ VALUE_3 }}**：{{ VALUE_3_DESC }}

### 在架构中的位置

\`\`\`mermaid
flowchart TB
    subgraph System["系统架构"]
        A["上游模块 A"]
        B["上游模块 B"]
        
        subgraph Current["📦 {{ MODULE_NAME }}"]
            style Current fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
            M["当前模块"]
        end
        
        C["下游模块 C"]
        D["下游模块 D"]
    end
    
    A --> M
    B --> M
    M --> C
    M --> D
\`\`\`

---

## ✨ 核心特性

| 特性 | 说明 | 相关接口 |
|------|------|----------|
| **{{ FEATURE_1 }}** | {{ FEATURE_1_DESC }} | [`{{ FEATURE_1_API }}`](#{{ FEATURE_1_API }}) |
| **{{ FEATURE_2 }}** | {{ FEATURE_2_DESC }} | [`{{ FEATURE_2_API }}`](#{{ FEATURE_2_API }}) |
| **{{ FEATURE_3 }}** | {{ FEATURE_3_DESC }} | [`{{ FEATURE_3_API }}`](#{{ FEATURE_3_API }}) |

### 核心类/接口

\`\`\`mermaid
classDiagram
class {{ CLASS_NAME }} {
  +{{ PROP_1 }} : {{ PROP_1_TYPE }}
  +{{ PROP_2 }} : {{ PROP_2_TYPE }}
  -{{ PRIVATE_PROP }} : {{ PRIVATE_TYPE }}
  +{{ METHOD_1 }}({{ PARAM }}: {{ PARAM_TYPE }}) : {{ RETURN_TYPE }}
  +{{ METHOD_2 }}() : void
}
class {{ RELATED_CLASS }} {
  +{{ RELATED_PROP }} : {{ RELATED_TYPE }}
}
{{ CLASS_NAME }} --> {{ RELATED_CLASS }} : 依赖
\`\`\`

**Diagram sources**
- [`{{ CLASS_FILE }}` L{{ START }}-L{{ END }}](../../../{{ CLASS_FILE_PATH }})

---

## 📁 文件结构

\`\`\`
{{ MODULE_PATH }}/
├── index.{{ EXT }}           # 模块入口，导出公开接口
├── {{ FILE_1 }}              # {{ FILE_1_DESC }}
├── {{ FILE_2 }}              # {{ FILE_2_DESC }}
├── {{ FILE_3 }}              # {{ FILE_3_DESC }}
├── types.{{ EXT }}           # 类型定义
└── __tests__/                # 单元测试
    └── {{ MODULE_NAME }}.test.{{ EXT }}
\`\`\`

### 文件职责说明

| 文件 | 职责 | 导出内容 |
|------|------|----------|
| `index.{{ EXT }}` | 模块入口 | 所有公开 API |
| `{{ FILE_1 }}` | {{ FILE_1_RESPONSIBILITY }} | {{ FILE_1_EXPORTS }} |
| `{{ FILE_2 }}` | {{ FILE_2_RESPONSIBILITY }} | {{ FILE_2_EXPORTS }} |

---

## 🔄 核心流程

### 主要工作流程

\`\`\`mermaid
flowchart TD
    Start["开始"] --> Input["接收输入"]
    Input --> Validate{"数据验证"}
    Validate -->|有效| Process["处理数据"]
    Validate -->|无效| Error["返回错误"]
    Process --> Transform["转换格式"]
    Transform --> Output["输出结果"]
    Output --> End["结束"]
    Error --> End
    
    style Start fill:#c8e6c9
    style End fill:#ffcdd2
    style Process fill:#fff9c4
\`\`\`

### 状态流转

\`\`\`mermaid
stateDiagram-v2
    [*] --> {{ STATE_1 }}: 初始化
    {{ STATE_1 }} --> {{ STATE_2 }}: {{ TRANSITION_1 }}
    {{ STATE_2 }} --> {{ STATE_3 }}: {{ TRANSITION_2 }}
    {{ STATE_3 }} --> {{ STATE_1 }}: {{ TRANSITION_3 }}
    {{ STATE_2 }} --> [*]: {{ TRANSITION_4 }}
\`\`\`

---

## 📖 公开接口

### 接口总览

| 接口 | 类型 | 描述 | 源码 |
|------|------|------|------|
| [`{{ FUNC_1 }}`](#{{ FUNC_1 }}) | 函数 | {{ FUNC_1_SHORT_DESC }} | [📄]({{ FUNC_1_SOURCE }}) |
| [`{{ FUNC_2 }}`](#{{ FUNC_2 }}) | 函数 | {{ FUNC_2_SHORT_DESC }} | [📄]({{ FUNC_2_SOURCE }}) |
| [`{{ CLASS_1 }}`](#{{ CLASS_1 }}) | 类 | {{ CLASS_1_SHORT_DESC }} | [📄]({{ CLASS_1_SOURCE }}) |
| [`{{ TYPE_1 }}`](#{{ TYPE_1 }}) | 类型 | {{ TYPE_1_SHORT_DESC }} | [📄]({{ TYPE_1_SOURCE }}) |

---

### `{{ FUNC_1 }}` [📄]({{ FUNC_1_SOURCE }})

> {{ FUNC_1_ONELINER }}

**详细描述**

{{ FUNC_1_DETAILED_DESC_PARA_1 }}

{{ FUNC_1_DETAILED_DESC_PARA_2 }}

**函数签名**

\`\`\`{{ LANG }}
{{ FUNC_1_SIGNATURE }}
\`\`\`

**参数**

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `{{ PARAM_1 }}` | `{{ PARAM_1_TYPE }}` | {{ PARAM_1_REQUIRED }} | {{ PARAM_1_DEFAULT }} | {{ PARAM_1_DESC }} |
| `{{ PARAM_2 }}` | `{{ PARAM_2_TYPE }}` | {{ PARAM_2_REQUIRED }} | {{ PARAM_2_DEFAULT }} | {{ PARAM_2_DESC }} |

**返回值**

| 类型 | 描述 |
|------|------|
| `{{ RETURN_TYPE }}` | {{ RETURN_DESC }} |

**使用示例**

\`\`\`{{ LANG }}
// 基础用法
{{ EXAMPLE_BASIC }}

// 带选项的用法
{{ EXAMPLE_WITH_OPTIONS }}

// 错误处理
{{ EXAMPLE_ERROR_HANDLING }}
\`\`\`

**注意事项**

- ⚠️ {{ WARNING_1 }}
- ⚠️ {{ WARNING_2 }}
- 💡 {{ TIP_1 }}

---

### `{{ TYPE_1 }}`

\`\`\`{{ LANG }}
{{ TYPE_DEFINITION }}
\`\`\`

| 属性 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `{{ PROP_1 }}` | `{{ PROP_1_TYPE }}` | {{ PROP_1_REQUIRED }} | {{ PROP_1_DESC }} |
| `{{ PROP_2 }}` | `{{ PROP_2_TYPE }}` | {{ PROP_2_REQUIRED }} | {{ PROP_2_DESC }} |

---

## 🚀 使用指南

### 快速开始

\`\`\`{{ LANG }}
// 1. 导入模块
{{ IMPORT_STATEMENT }}

// 2. 基本使用
{{ BASIC_USAGE }}

// 3. 查看结果
{{ CHECK_RESULT }}
\`\`\`

### 常见用例

#### 用例 1：{{ USE_CASE_1_TITLE }}

**场景**：{{ USE_CASE_1_SCENARIO }}

\`\`\`{{ LANG }}
{{ USE_CASE_1_CODE }}
\`\`\`

**预期输出**：

\`\`\`
{{ USE_CASE_1_OUTPUT }}
\`\`\`

#### 用例 2：{{ USE_CASE_2_TITLE }}

**场景**：{{ USE_CASE_2_SCENARIO }}

\`\`\`{{ LANG }}
{{ USE_CASE_2_CODE }}
\`\`\`

#### 用例 3：{{ USE_CASE_3_TITLE }}

**场景**：{{ USE_CASE_3_SCENARIO }}

\`\`\`{{ LANG }}
{{ USE_CASE_3_CODE }}
\`\`\`

---

## ✅ 最佳实践

### 推荐做法

| 做法 | 原因 |
|------|------|
| ✅ {{ BEST_PRACTICE_1 }} | {{ BEST_PRACTICE_1_REASON }} |
| ✅ {{ BEST_PRACTICE_2 }} | {{ BEST_PRACTICE_2_REASON }} |
| ✅ {{ BEST_PRACTICE_3 }} | {{ BEST_PRACTICE_3_REASON }} |

### 应该避免

| 做法 | 原因 |
|------|------|
| ❌ {{ ANTI_PATTERN_1 }} | {{ ANTI_PATTERN_1_REASON }} |
| ❌ {{ ANTI_PATTERN_2 }} | {{ ANTI_PATTERN_2_REASON }} |

### 性能优化

- **{{ PERF_TIP_1_TITLE }}**：{{ PERF_TIP_1_DESC }}
- **{{ PERF_TIP_2_TITLE }}**：{{ PERF_TIP_2_DESC }}

---

## 🎨 设计决策

### 为什么选择当前实现

{{ DESIGN_DECISION_INTRO }}

### 考虑过的替代方案

| 方案 | 优点 | 缺点 | 未选择原因 |
|------|------|------|------------|
| {{ ALT_1 }} | {{ ALT_1_PROS }} | {{ ALT_1_CONS }} | {{ ALT_1_REJECT_REASON }} |
| {{ ALT_2 }} | {{ ALT_2_PROS }} | {{ ALT_2_CONS }} | {{ ALT_2_REJECT_REASON }} |

### 权衡取舍

{{ TRADEOFFS_DESC }}

---

## 🔍 内部实现原理

> 本节面向需要深入理解或修改模块的开发者

### 核心算法

{{ CORE_ALGORITHM_DESC }}

\`\`\`mermaid
flowchart TD
    {{ ALGORITHM_FLOWCHART }}
\`\`\`

### 数据流

\`\`\`mermaid
sequenceDiagram
    {{ DATA_FLOW_SEQUENCE }}
\`\`\`

---

## ⚠️ 错误处理

### 可能的错误

| 错误类型 | 触发条件 | 处理建议 |
|----------|----------|----------|
| `{{ ERROR_1 }}` | {{ ERROR_1_CONDITION }} | {{ ERROR_1_SOLUTION }} |
| `{{ ERROR_2 }}` | {{ ERROR_2_CONDITION }} | {{ ERROR_2_SOLUTION }} |

### 调试技巧

1. **{{ DEBUG_TIP_1_TITLE }}**
   - {{ DEBUG_TIP_1_DESC }}

2. **{{ DEBUG_TIP_2_TITLE }}**
   - {{ DEBUG_TIP_2_DESC }}

---

## 🔗 依赖关系

### 依赖图

\`\`\`mermaid
flowchart LR
    subgraph Dependencies["依赖的模块"]
        D1["{{ DEP_1 }}"]
        D2["{{ DEP_2 }}"]
    end
    
    M["📦 {{ MODULE_NAME }}"]
    
    subgraph Dependents["被依赖"]
        R1["{{ DEPENDENT_1 }}"]
        R2["{{ DEPENDENT_2 }}"]
    end
    
    D1 --> M
    D2 --> M
    M --> R1
    M --> R2
    
    style M fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
\`\`\`

### 依赖说明

| 依赖模块 | 用途 | 耦合程度 |
|----------|------|----------|
| [`{{ DEP_1 }}`]({{ DEP_1_LINK }}) | {{ DEP_1_PURPOSE }} | {{ DEP_1_COUPLING }} |
| [`{{ DEP_2 }}`]({{ DEP_2_LINK }}) | {{ DEP_2_PURPOSE }} | {{ DEP_2_COUPLING }} |

---

## 📄 相关文档

| 文档 | 描述 |
|------|------|
| [架构文档](../architecture.md#{{ MODULE_ANCHOR }}) | 模块在架构中的位置 |
| [API 参考](../api/{{ MODULE_NAME }}.md) | 完整 API 文档 |
| [{{ RELATED_MODULE_1 }}]({{ RELATED_MODULE_1 }}.md) | 相关模块 |
| [{{ RELATED_MODULE_2 }}]({{ RELATED_MODULE_2 }}.md) | 相关模块 |

---

## 📝 变更历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| {{ VERSION_1 }} | {{ DATE_1 }} | {{ CHANGE_1 }} |
| {{ VERSION_2 }} | {{ DATE_2 }} | {{ CHANGE_2 }} |

---

[← 返回模块列表](_index.md) | [查看 API 参考 →](../api/{{ MODULE_NAME }}.md)

*由 [Mini-Wiki v{{ MINI_WIKI_VERSION }}](https://github.com/trsoliu/mini-wiki) 自动生成 | {{ GENERATED_AT }}*
```

---

## API 参考模板

```markdown
# API 参考: {{ MODULE_NAME }}

> {{ MODULE_DESCRIPTION }}

---

## 📋 概述

### 模块用途

{{ MODULE_PURPOSE_DETAILED }}

### 导入方式

\`\`\`{{ LANG }}
// 推荐：按需导入
import { {{ NAMED_EXPORTS }} } from '{{ PACKAGE_PATH }}';

// 或：导入全部
import * as {{ MODULE_ALIAS }} from '{{ PACKAGE_PATH }}';
\`\`\`

### 快速示例

\`\`\`{{ LANG }}
{{ QUICK_EXAMPLE }}
\`\`\`

---

## 📚 接口总览

| 接口 | 类型 | 描述 | 源码 |
|------|------|------|------|
{{ API_OVERVIEW_TABLE }}

---

## 📝 类型定义

### `{{ TYPE_NAME }}`

> {{ TYPE_DESCRIPTION }}

\`\`\`{{ LANG }}
{{ TYPE_DEFINITION }}
\`\`\`

| 属性 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
{{ TYPE_PROPERTIES_TABLE }}

**使用示例**：

\`\`\`{{ LANG }}
{{ TYPE_USAGE_EXAMPLE }}
\`\`\`

---

## 🔧 函数

### `{{ FUNCTION_NAME }}` [`📄`](../../../{{ SOURCE_PATH }})

> {{ FUNCTION_ONELINER }}

**详细描述**

{{ FUNCTION_DETAILED_DESC_PARA_1 }}

{{ FUNCTION_DETAILED_DESC_PARA_2 }}

该函数主要用于 {{ FUNCTION_USE_CASE }}。在 {{ FUNCTION_CONTEXT }} 场景下特别有用。

**函数签名**

\`\`\`{{ LANG }}
{{ FUNCTION_SIGNATURE }}
\`\`\`

**参数详解**

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
{{ PARAMS_TABLE }}

**参数约束**：
- `{{ PARAM_1 }}`：{{ PARAM_1_CONSTRAINTS }}
- `{{ PARAM_2 }}`：{{ PARAM_2_CONSTRAINTS }}

**返回值**

| 类型 | 描述 |
|------|------|
| `{{ RETURN_TYPE }}` | {{ RETURN_DETAILED_DESC }} |

**返回值可能的情况**：
- 成功时：{{ SUCCESS_RETURN }}
- 失败时：{{ FAILURE_RETURN }}

**异常**

| 异常类型 | 触发条件 | 处理建议 |
|----------|----------|----------|
{{ EXCEPTIONS_TABLE }}

**示例**

\`\`\`{{ LANG }}
// 示例 1：基础用法
{{ EXAMPLE_1 }}

// 示例 2：带完整选项
{{ EXAMPLE_2 }}

// 示例 3：错误处理
{{ EXAMPLE_3 }}
\`\`\`

**注意事项**

- ⚠️ {{ WARNING_1 }}
- ⚠️ {{ WARNING_2 }}
- 💡 {{ TIP_1 }}

**相关接口**

| 接口 | 关系 |
|------|------|
| [`{{ RELATED_1 }}`](#{{ RELATED_1 }}) | {{ RELATION_1_DESC }} |
| [`{{ RELATED_2 }}`](#{{ RELATED_2 }}) | {{ RELATION_2_DESC }} |

---

## 🏛 类

### `{{ CLASS_NAME }}` [`📄`](../../../{{ CLASS_SOURCE_PATH }})

> {{ CLASS_DESCRIPTION }}

**类图**

\`\`\`mermaid
classDiagram
    class {{ CLASS_NAME }} {
        {{ CLASS_PROPERTIES }}
        {{ CLASS_METHODS }}
    }
    {{ CLASS_RELATIONSHIPS }}
\`\`\`

#### 构造函数

\`\`\`{{ LANG }}
{{ CONSTRUCTOR_SIGNATURE }}
\`\`\`

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
{{ CONSTRUCTOR_PARAMS }}

#### 属性

| 属性 | 类型 | 访问 | 描述 |
|------|------|------|------|
{{ CLASS_PROPERTIES_TABLE }}

#### 方法

##### `{{ METHOD_NAME }}()`

{{ METHOD_DESCRIPTION }}

\`\`\`{{ LANG }}
{{ METHOD_SIGNATURE }}
\`\`\`

| 参数 | 类型 | 描述 |
|------|------|------|
{{ METHOD_PARAMS }}

**返回值**：`{{ METHOD_RETURN_TYPE }}` - {{ METHOD_RETURN_DESC }}

#### 完整示例

\`\`\`{{ LANG }}
{{ CLASS_COMPLETE_EXAMPLE }}
\`\`\`

---

## 📖 使用模式

### 模式 1：{{ PATTERN_1_TITLE }}

**场景**：{{ PATTERN_1_SCENARIO }}

\`\`\`{{ LANG }}
{{ PATTERN_1_CODE }}
\`\`\`

**说明**：{{ PATTERN_1_EXPLANATION }}

### 模式 2：{{ PATTERN_2_TITLE }}

**场景**：{{ PATTERN_2_SCENARIO }}

\`\`\`{{ LANG }}
{{ PATTERN_2_CODE }}
\`\`\`

### 模式 3：{{ PATTERN_3_TITLE }}

**场景**：{{ PATTERN_3_SCENARIO }}

\`\`\`{{ LANG }}
{{ PATTERN_3_CODE }}
\`\`\`

---

## ❓ 常见问题

### Q: {{ FAQ_1_QUESTION }}

**A**: {{ FAQ_1_ANSWER }}

\`\`\`{{ LANG }}
{{ FAQ_1_CODE }}
\`\`\`

### Q: {{ FAQ_2_QUESTION }}

**A**: {{ FAQ_2_ANSWER }}

### Q: {{ FAQ_3_QUESTION }}

**A**: {{ FAQ_3_ANSWER }}

---

## 📄 相关文档

| 文档 | 描述 |
|------|------|
| [模块文档](../modules/{{ MODULE_NAME }}.md) | 模块概览和设计说明 |
| [架构文档](../architecture.md) | 系统架构 |
| [{{ RELATED_API_1 }}]({{ RELATED_API_1 }}.md) | 相关 API |

---

[← 返回 API 列表](_index.md) | [查看模块文档 →](../modules/{{ MODULE_NAME }}.md)

*由 [Mini-Wiki v{{ MINI_WIKI_VERSION }}](https://github.com/trsoliu/mini-wiki) 自动生成 | {{ GENERATED_AT }}*
```

---

## 快速开始模板

```markdown
# 快速开始

> 本指南帮助你在 **5 分钟内** 上手 {{ PROJECT_NAME }}

---

## 📋 前置条件

### 环境要求

| 依赖 | 最低版本 | 推荐版本 | 检查命令 |
|------|----------|----------|----------|
| {{ DEP_1 }} | {{ DEP_1_MIN }} | {{ DEP_1_REC }} | `{{ DEP_1_CHECK }}` |
| {{ DEP_2 }} | {{ DEP_2_MIN }} | {{ DEP_2_REC }} | `{{ DEP_2_CHECK }}` |

### 前置知识

- {{ PREREQUISITE_1 }}
- {{ PREREQUISITE_2 }}

---

## 🚀 安装

### 方式一：包管理器（推荐）

\`\`\`bash
# npm
npm install {{ PACKAGE_NAME }}

# yarn
yarn add {{ PACKAGE_NAME }}

# pnpm
pnpm add {{ PACKAGE_NAME }}
\`\`\`

### 方式二：从源码安装

\`\`\`bash
git clone {{ REPO_URL }}
cd {{ PROJECT_NAME }}
{{ BUILD_COMMAND }}
\`\`\`

### 验证安装

\`\`\`bash
{{ VERIFY_COMMAND }}
# 预期输出: {{ VERIFY_OUTPUT }}
\`\`\`

---

## ⚙️ 配置

### 基础配置

\`\`\`bash
# 复制配置模板
cp {{ CONFIG_TEMPLATE }} {{ CONFIG_FILE }}
\`\`\`

### 配置文件说明

\`\`\`{{ CONFIG_LANG }}
{{ CONFIG_EXAMPLE }}
\`\`\`

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `{{ CONFIG_1 }}` | `{{ CONFIG_1_TYPE }}` | `{{ CONFIG_1_DEFAULT }}` | {{ CONFIG_1_DESC }} |
| `{{ CONFIG_2 }}` | `{{ CONFIG_2_TYPE }}` | `{{ CONFIG_2_DEFAULT }}` | {{ CONFIG_2_DESC }} |

### 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `{{ ENV_1 }}` | {{ ENV_1_DESC }} | `{{ ENV_1_EXAMPLE }}` |

---

## 🏃 启动

### 开发模式

\`\`\`bash
{{ DEV_COMMAND }}
\`\`\`

### 生产模式

\`\`\`bash
{{ PROD_COMMAND }}
\`\`\`

### 验证启动

{{ VERIFY_START_DESC }}

\`\`\`
{{ VERIFY_START_OUTPUT }}
\`\`\`

---

## 📝 第一个示例

### 步骤 1：创建入口文件

\`\`\`{{ LANG }}
// {{ EXAMPLE_FILE }}
{{ EXAMPLE_STEP_1 }}
\`\`\`

### 步骤 2：添加核心逻辑

\`\`\`{{ LANG }}
{{ EXAMPLE_STEP_2 }}
\`\`\`

### 步骤 3：运行并查看结果

\`\`\`bash
{{ RUN_EXAMPLE_COMMAND }}
\`\`\`

**预期输出**：

\`\`\`
{{ EXAMPLE_OUTPUT }}
\`\`\`

---

## 🎯 下一步

恭喜！你已经成功运行了第一个示例。接下来可以：

| 目标 | 推荐阅读 |
|------|----------|
| 了解系统架构 | [架构概览](architecture.md) |
| 深入学习各模块 | [模块文档](modules/_index.md) |
| 查阅 API 详情 | [API 参考](api/_index.md) |
| 查看更多示例 | [示例集合](examples/_index.md) |

---

## ❓ 常见问题

### Q: {{ SETUP_FAQ_1_Q }}

**A**: {{ SETUP_FAQ_1_A }}

\`\`\`bash
{{ SETUP_FAQ_1_CMD }}
\`\`\`

### Q: {{ SETUP_FAQ_2_Q }}

**A**: {{ SETUP_FAQ_2_A }}

---

## 🆘 获取帮助

- 📖 [完整文档](index.md)
- 🐛 [报告问题]({{ ISSUES_URL }})
- 💬 [社区讨论]({{ DISCUSSIONS_URL }})

---

[← 返回首页](index.md) | [查看架构 →](architecture.md)

*由 [Mini-Wiki v{{ MINI_WIKI_VERSION }}](https://github.com/trsoliu/mini-wiki) 自动生成 | {{ GENERATED_AT }}*
```

---

## 文档索引模板

```markdown
# 文档地图

> {{ PROJECT_NAME }} 完整文档索引与阅读指南

---

## 🗺 文档关系图

\`\`\`mermaid
flowchart TB
    subgraph Entry["📚 入口"]
        Index["首页<br/>index.md"]
        GS["快速开始<br/>getting-started.md"]
    end
    
    subgraph Core["🏗 核心文档"]
        Arch["架构概览<br/>architecture.md"]
        Modules["模块文档<br/>modules/"]
        API["API 参考<br/>api/"]
    end
    
    subgraph Details["📖 详细文档"]
        M1["模块 1"]
        M2["模块 2"]
        A1["API 1"]
        A2["API 2"]
    end
    
    Index --> GS
    Index --> Arch
    GS --> Arch
    Arch --> Modules
    Arch --> API
    Modules --> M1
    Modules --> M2
    API --> A1
    API --> A2
    M1 -.-> A1
    M2 -.-> A2
    
    style Index fill:#e3f2fd
    style Arch fill:#fff3e0
    style Modules fill:#e8f5e9
    style API fill:#fce4ec
\`\`\`

---

## 📖 阅读路径推荐

### 🚀 新手入门

1. [首页](index.md) - 了解项目概况
2. [快速开始](getting-started.md) - 5 分钟上手
3. [架构概览](architecture.md) - 理解整体结构
4. 选择感兴趣的 [模块文档](modules/_index.md)

### 🏗 架构理解

1. [架构概览](architecture.md) - 系统设计
2. [模块划分](architecture.md#模块划分详解) - 模块职责
3. 各 [模块文档](modules/_index.md) - 深入细节

### 📖 API 查阅

1. [API 索引](api/_index.md) - 找到目标 API
2. 具体 API 文档 - 查看详情
3. [使用示例](#) - 实践应用

---

## 📑 完整文档索引

### 入口文档

| 文档 | 描述 |
|------|------|
| [index.md](index.md) | 项目首页 |
| [getting-started.md](getting-started.md) | 快速开始指南 |
| [architecture.md](architecture.md) | 系统架构 |

### 模块文档

| 模块 | 描述 | API |
|------|------|-----|
{{ MODULES_INDEX_TABLE }}

### API 文档

| API | 所属模块 | 描述 |
|-----|----------|------|
{{ API_INDEX_TABLE }}

---

## 🔗 模块依赖矩阵

| 模块 | 依赖 | 被依赖 |
|------|------|--------|
{{ DEPENDENCY_MATRIX }}

---

[← 返回首页](index.md)

*由 [Mini-Wiki v{{ MINI_WIKI_VERSION }}](https://github.com/trsoliu/mini-wiki) 自动生成 | {{ GENERATED_AT }}*
```

---

## 配置模板

```yaml
# Mini-Wiki 配置文件
# 详细说明请参考文档

# 生成配置
generation:
  # 文档语言：zh / en / both
  language: zh
  
  # 文档档位：overview / module-complete / topic / api-complete / auto
  doc_profile: module-complete
  
  # 内容详细程度：minimal / standard / detailed
  detail_level: detailed
  
  # 是否包含 Mermaid 图表
  include_diagrams: true
  
  # 是否包含代码示例
  include_examples: true
  
  # 是否链接到源码
  link_to_source: true
  
  # 默认直接发布：通过质量门禁即可发布
  # true: draft/reviewed 不能直接发布
  # false: 允许在未审批时发布（默认）
  publish_requires_approval: false
  
  # 单个文件最大处理大小（字节）
  max_file_size: 100000
  
  # 每个模块文档的最小章节数
  min_sections: 10

# 图表配置
diagrams:
  # 架构图样式
  architecture_style: flowchart TB
  
  # 数据流图样式  
  dataflow_style: sequenceDiagram
  
  # 是否使用颜色区分模块
  use_colors: true

# 文档关联
linking:
  # 自动生成交叉链接
  auto_cross_links: true
  
  # 生成文档地图
  generate_doc_map: true
  
  # 生成依赖关系图
  generate_dependency_graph: true

# 排除配置
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
  - "*.spec.js"
  - "*.test.js"
  - "*.spec.ts"

# 模块分类规则
module_categories:
  core:
    - core
    - lib
    - engine
  ui:
    - components
    - views
    - pages
  api:
    - api
    - services
    - handlers
  utils:
    - utils
    - helpers
    - common
```
