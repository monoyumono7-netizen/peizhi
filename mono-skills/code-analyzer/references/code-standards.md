# 图表与代码规范

分析文档中的图表和代码引用必须遵循以下规范。

## 核心原则：图表优先，代码辅助

- **图表是主要表达手段** — 先用图讲清楚流程、关系、状态变化
- **代码是辅助说明** — 用精简代码帮助理解具体实现，不是文档主体
- **目标是说清楚** — 不追求代码量，追求表达清晰

## 图表规范

### 图表丰富度要求

每个文档至少包含 **2 种不同类型** 的 Mermaid 图（3 个相同类型的 flowchart 不满足要求）。

| 文档类型 | 必选图 | 可选图 |
|---------|--------|--------|
| 架构总览 | flowchart TD（全景流程）+ flowchart LR（模块关系） | — |
| 流程分析 | sequenceDiagram（模块交互） | stateDiagram-v2（状态变化）、flowchart（数据流转） |

### 可用图表类型

| 图表类型 | 适用场景 |
|---------|---------|
| `flowchart TD` | 流程步骤、架构分层 |
| `flowchart LR` | 模块依赖、数据流向 |
| `sequenceDiagram` | 模块间交互、请求/响应 |
| `stateDiagram-v2` | 状态变化、生命周期 |
| `classDiagram` | 类型结构、接口关系（可选） |
| `erDiagram` | 数据模型关系（可选） |

### Mermaid 语法安全规则

**必须遵守，否则图表渲染会失败：**

1. **Node labels 必须加引号**
   ```mermaid
   %% 正确
   A["CLI Entry"] --> B["Source Index"]
   %% 错误
   A[CLI Entry] --> B[Source Index]
   ```

2. **Node ID 只用英文字母数字**
   ```mermaid
   %% 正确
   CoreModule["核心模块"]
   %% 错误
   CoreModule.123["核心模块"]
   ```

3. **subgraph ID 用英文，不和 node ID 冲突**
   ```mermaid
   %% 正确
   subgraph CL["CLI Layer"]
       CLI["cli.ts"] --> C2["commands"]
   end
   %% 错误（subgraph ID "CLI" 和 node ID "CLI" 冲突）
   subgraph CLI["CLI Layer"]
       CLI["cli.ts"]
   end
   ```

4. **内嵌引号用 HTML entity**
   ```mermaid
   %% 正确
   A["Config &quot;key&quot; value"]
   %% 错误
   A["Config "key" value"]
   ```

5. **复杂度控制**
   - 节点 ≤ 6：不需要分组
   - 节点 7-12：用 subgraph 分组
   - 节点 > 20：拆成多个图

## 代码引用规范

### 代码形式

代码可以是以下任意形式，以说清楚逻辑为目标：

- **真实代码片段** — 从源文件中摘取的关键代码
- **伪代码** — 用自然语言 + 代码结构描述逻辑
- **简化代码** — 省略细节，保留核心逻辑

### 引用格式

```typescript
// 文件路径:行号范围（引用真实代码时标注）
const example = () => {
  // 关键逻辑说明
}
```

### Emoji 标记（可选）

| 标记 | 含义 | 使用场景 |
|-----|------|---------|
| `💡` | 设计意图 | 解释为什么这样写 |
| `🔄` | 数据流向 | 标记数据流转方向 |
| `⚠️` | 注意事项 | 容易出问题的地方 |

### 代码量

不设硬性代码占比要求。原则：
- 图表已经说清楚的，不需要再贴代码
- 代码只在"图表无法表达的实现细节"时使用
- 每段代码配简要文字说明
