# 代码引用规范

分析文档中的代码引用必须遵循以下规范，确保文档的可读性和教学性。

## 代码引用格式

### 标注格式

```typescript
// 📁 src/hooks/useExample.ts:15-25
const useExample = () => {
  // 👆 这里使用了 xxx 模式
  const [state, setState] = useState()
  // ...
}
```

### Emoji 标记系统

| 标记 | 含义 | 使用场景 |
|-----|------|---------|
| `📁` | 文件位置 | 每段代码开头标注文件路径和行号 |
| `👆` | 关键点 | 标记当前行的重要概念 |
| `👇` | 下文关键 | 提示下面代码的重点 |
| `💡` | 设计意图 | 解释为什么这样写 |
| `🔄` | 数据流向 | 标记数据流转方向 |
| `⚠️` | 注意事项 | 容易踩坑的地方 |
| `✨` | 亮点技巧 | 值得学习的写法 |

## 代码引用原则

### 真实代码优先

- **必须引用真实源码**，不可编造代码
- 可以省略非关键部分（用 `// ...` 表示）
- 伪代码仅在描述整体流程时作为辅助

### 代码解释要求

每段引用代码必须配有解释，包含：

1. **做什么**（What）— 这段代码的功能
2. **为什么**（Why）— 为什么这样实现
3. **怎么做**（How）— 关键技术点

**示例：**

```markdown
下面这段代码实现了请求取消机制：

// 📁 hooks/use-cancellable-toolcall.ts:23-35
export const useCancellableToolCall = (messages: Message[]) => {
  // 💡 使用白名单判断工具是否可取消
  const cancellableTools = messages
    .filter(m => CANCELLABLE_WHITELIST.includes(m.toolName))
    .filter(m => m.uiStatus === 'rendering')
  // ✨ 只返回正在执行中的可取消工具
  return { cancellableTools, hasCancellable: cancellableTools.length > 0 }
}

**技术要点：**
- 白名单机制避免误取消关键工具
- 只检测 `rendering` 状态，已完成的不可取消
```

### 代码量要求

| 文档类型 | 代码占比 | 说明 |
|---------|---------|------|
| 架构总览 | 30-40% | 入口代码 + 核心流程代码链路 |
| 模块分析 | 40-60% | 接口定义 + 实现细节 + 代码片段 |
| 流程分析 | 50-60% | 逐步代码追踪为主 |

### 流程追踪的代码链路

流程分析中，必须完整展示代码调用链：

```markdown
### 步骤 1：用户触发操作

// 📁 Component.tsx:45-52
const handleClick = () => {
  // 👇 调用 service 层
  fetchData(params)
}

### 步骤 2：Service 层处理

// 📁 services/api.ts:20-35
export const fetchData = async (params) => {
  // 🔄 数据流向：params -> request -> transform -> return
  const response = await request.get('/api/xxx', params)
  return transform(response)
}

### 步骤 3：状态更新
// ...
```

每个步骤之间要有连贯的代码调用关系，读者应能顺着代码理解完整流程。
