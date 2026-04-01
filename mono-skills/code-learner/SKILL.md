---
name: code-learner
description: 深度分析项目或目录代码，帮助用户快速理解陌生代码库。当用户说"分析下这里"、"教我这个代码"、"帮我理解这个项目"、"这个目录在干什么"、"学习这个代码"时触发此 skill。输出结构化的 Markdown 文档到桌面 markdown 文件夹。
---

# 代码学习助手

帮助前端开发者快速理解陌生项目或目录的代码架构、实现逻辑和设计模式。

## 输出目录规则

**统一输出到桌面 markdown 文件夹，按项目分类**

### 确定项目名称

```bash
# 优先使用 git 仓库名
PROJECT_NAME=$(basename $(git rev-parse --show-toplevel 2>/dev/null) 2>/dev/null)

# 如果不是 git 仓库，使用当前目录名
if [ -z "$PROJECT_NAME" ]; then
  PROJECT_NAME=$(basename $(pwd))
fi
```

### 输出路径

```
/Users/mono/Desktop/markdown/{项目名}/
├── {项目名}-{目录名}-概览.md       # 阶段 1 输出
├── {项目名}-{目录名}-{文件名}.md   # 阶段 3 深入分析
└── {项目名}-{目录名}-索引.md       # 阶段 4 总结
```

**示例**（分析 cocraft 项目的 AiAssistant 目录）：
```
/Users/mono/Desktop/markdown/cocraft/
├── cocraft-AiAssistant-概览.md
├── cocraft-AiAssistant-assistant-fusion.md
├── cocraft-AiAssistant-useAssistant.md
└── cocraft-AiAssistant-索引.md
```

## 工作流程

### 阶段 1：全局概览分析

1. **确定分析范围**
   - 用户指定的目录路径
   - 若未指定，询问用户要分析的目录

2. **执行全局分析**
   - 扫描目录结构（使用 Glob）
   - 识别入口文件（index.ts/tsx, main.ts, App.tsx 等）
   - 识别 package.json 获取依赖和技术栈
   - 分析目录组织模式

3. **生成概览文档**（参考 [references/overview-template.md](references/overview-template.md)）
   - 项目/目录的核心职责
   - 技术栈和依赖
   - 目录结构说明
   - 入口文件和核心流程
   - 状态管理方式
   - 数据流图（Mermaid）

4. **输出**：`/Users/mono/Desktop/markdown/{项目名}/{项目名}-{目录名}-概览.md`

### 阶段 2：识别重点文件

分析完概览后，识别需要深入分析的重点文件：

**识别标准：**
- 入口文件和核心模块
- 包含复杂业务逻辑的文件（行数 > 200）
- 状态管理相关文件
- 关键 hooks 和工具函数
- 包含设计模式的实现

**输出重点文件清单给用户确认**

### 阶段 3：深入分析

对每个重点文件生成详细分析文档（参考 [references/deep-dive-template.md](references/deep-dive-template.md)）：

1. **代码结构分析**
   - 导出的函数/组件/类
   - 内部依赖关系
   - 关键代码段落解读（带代码片段）

2. **设计模式识别**
   - 使用的设计模式及其好处
   - 可复用的代码模式

3. **实现亮点**
   - 优秀的代码实践
   - 值得学习的技巧

4. **输出**：`/Users/mono/Desktop/markdown/{项目名}/{项目名}-{目录名}-{文件名}.md`

### 阶段 4：总结

生成索引文件，包含：
- 所有分析文档的链接
- 学习路径建议（推荐阅读顺序）
- 快速参考卡片

**输出**：`/Users/mono/Desktop/markdown/{项目名}/{项目名}-{目录名}-索引.md`

## 交互要点

1. **阶段 1 完成后**：展示概览摘要，询问是否继续深入分析
2. **阶段 2 完成后**：展示重点文件清单，让用户确认或调整
3. **阶段 3 进行时**：每完成一个文件，简要汇报进度

## 代码引用规范（核心原则）

**原则：让代码说话，用代码教学**

分析文档必须大量引用原始代码，做到"边看代码边学习"。每个概念、流程、模式都要有对应的代码支撑。

### 引用格式

```typescript
// 📁 src/hooks/useExample.ts:15-25
const useExample = () => {
  // 👆 这里使用了 xxx 模式
  const [state, setState] = useState()
  // ...
}
```

### 代码注释标记

在引用的代码中使用 emoji 标记关键点：

| 标记 | 含义 | 使用场景 |
|-----|------|---------|
| `👆` | 关键点 | 标记当前行的重要概念 |
| `👇` | 下文关键 | 提示下面代码的重点 |
| `💡` | 设计意图 | 解释为什么这样写 |
| `🔄` | 数据流向 | 标记数据流转方向 |
| `⚠️` | 注意事项 | 容易踩坑的地方 |
| `✨` | 亮点技巧 | 值得学习的写法 |

### 流程分析的代码要求

**阶段 1 概览中的流程分析必须包含：**

1. **入口代码完整展示**
   ```typescript
   // 📁 index.ts:1-30 - 入口文件，展示模块的整体导出结构
   // [完整引用入口文件的关键导出部分]
   ```

2. **核心流程逐步代码追踪**
   ```markdown
   ### 流程步骤 1：用户触发操作

   用户点击按钮后，触发 `handleClick`：

   // 📁 Component.tsx:45-52
   const handleClick = () => {
     // 👇 这里调用了 service 层
     fetchData(params)
   }

   ### 流程步骤 2：Service 层处理

   `fetchData` 内部实现：

   // 📁 services/api.ts:20-35
   export const fetchData = async (params) => {
     // 💡 使用了请求拦截器统一处理 token
     const response = await request.get('/api/xxx', params)
     // 🔄 数据流向：response -> transform -> store
     return transform(response)
   }

   ### 流程步骤 3：状态更新
   ...
   ```

3. **状态变化代码链路**
   - 从触发点到状态定义，完整展示代码调用链
   - 每个环节都要有代码片段

### 代码解释深度要求

每段引用的代码必须配有解释，解释应包含：

1. **这段代码做什么**（What）
2. **为什么这样实现**（Why）
3. **关键技术点**（How）

**示例：**

```markdown
下面这段代码实现了请求的自动重试机制：

// 📁 utils/request.ts:78-95
export const retryRequest = async (fn, retries = 3) => {
  // 💡 为什么用递归而不是循环？
  // 因为需要在每次重试之间 await 延迟，递归更清晰
  try {
    return await fn()
  } catch (error) {
    if (retries > 0) {
      // ✨ 指数退避策略：每次重试等待时间翻倍
      await delay(1000 * (4 - retries))
      return retryRequest(fn, retries - 1)  // 🔄 递归调用
    }
    throw error
  }
}

**技术要点：**
- 使用递归实现重试，代码更简洁
- 指数退避避免请求风暴
- 保留原始错误，便于上层处理
```

### 代码量要求

| 文档类型 | 代码占比 | 说明 |
|---------|---------|------|
| 00-overview.md | 40-50% | 入口代码 + 核心流程代码链路 |
| 深入分析文档 | 50-60% | 大量代码片段 + 逐行解释 |

**切记**：宁可多引用代码，不可空讲概念。用户是来"看代码学习"的，不是来看文字描述的。

## 前端项目专注点

针对前端项目，重点关注：
- React 组件设计模式
- 状态管理实现（Redux/Zustand/Context/RxJS）
- 自定义 Hooks 的设计
- API 调用和数据获取模式
- 性能优化手段
- TypeScript 类型设计
