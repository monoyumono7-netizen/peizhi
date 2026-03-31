# Skills 全局统一管理 - 最终配置

## ✅ 完成状态

**所有 skills 已统一到全局目录，所有 agents 共享！**

## 📊 统计

- **总共 29 个 skills** 在 `~/.openclaw/skills-global/`
- **30/70 skills 可用** (OpenClaw 识别)
- **所有 agents** (boss, search, 以及未来的新 agents) 都可以使用

## 📁 Skills 列表

### 全局 Skills 目录: `~/.openclaw/skills-global/`

1. **agent-monitor** - Agent 健康监控
2. **ai-automation-workflows** - AI 自动化工作流
3. **answeroverflow** - AnswerOverflow 集成
4. **api-gateway** - API 网关
5. **automation-workflows** - 自动化工作流
6. **caldav-calendar** - CalDAV 日历
7. **chrome-debug** - Chrome 调试
8. **code-delegate** - 代码委托
9. **elite-longterm-memory** - 长期记忆
10. **fact-checker** - 事实核查
11. **gh-action-gen** - GitHub Actions 生成
12. **github** - GitHub 集成
13. **github-cli** - GitHub CLI
14. **github-mcp** - GitHub MCP
15. **gog** - Google Workspace
16. **multi-agent** - 多 Agent 管理
17. **ontology** - 本体论
18. **openclaw-github-assistant** - GitHub 助手
19. **pr-reviewer** - PR 审查
20. **self-improving-agent** - 自我改进 Agent
21. **skill-optimizer** - Skill 优化分析
22. **slack** - Slack 集成
23. **sonoscli** - Sonos 控制
24. **summarize** - 摘要生成
25. **tavily-search** - Tavily 搜索
26. **trello** - Trello 集成
27. **twitter** - Twitter 集成
28. **weather** - 天气查询
29. **windows-ui-automation** - Windows UI 自动化

## 🔧 配置

### OpenClaw 配置 (`~/.openclaw/openclaw.json`)

```json
{
  "skills": {
    "load": {
      "extraDirs": ["~/.openclaw/skills-global"],
      "watch": true
    }
  }
}
```

### 目录结构

```
~/.openclaw/
├── skills-global/              # ⭐ 所有 agents 共享的 skills (29个)
│   ├── agent-monitor/
│   ├── ai-automation-workflows/
│   ├── answeroverflow/
│   ├── ... (其他 26 个)
│   └── windows-ui-automation/
│
├── workspace/                  # 默认 workspace
│   └── skills/                 # 空 (已全部移到 skills-global)
│
├── workspace-boss/             # boss agent
│   └── skills/                 # 空 (使用 skills-global)
│
└── workspace-search/           # search agent
    └── skills/                 # 空 (使用 skills-global)
```

## 📝 使用指南

### 添加新 Skill

**所有新 skills 都添加到 `~/.openclaw/skills-global/`：**

```bash
# 方法 1: 手动创建
cd ~/.openclaw/skills-global
mkdir my-new-skill
cd my-new-skill
# 创建 SKILL.md 和 scripts/

# 方法 2: 从 ClawHub 安装
clawhub install <skill-name>
# 然后移动到 skills-global
mv ~/.openclaw/workspace/skills/<skill-name> ~/.openclaw/skills-global/

# 方法 3: 使用 skill-creator
# 在 skills-global 目录中创建
```

### 更新 Skill

```bash
# 直接在 skills-global 中修改
cd ~/.openclaw/skills-global/<skill-name>
# 编辑文件...

# OpenClaw 会自动检测变化 (watch: true)
# 所有 agents 在下次对话时自动使用新版本
```

### 删除 Skill

```bash
# 从 skills-global 删除
rm -rf ~/.openclaw/skills-global/<skill-name>

# 所有 agents 将不再能使用该 skill
```

### Agent 特定的 Skill

如果某个 skill 只对特定 agent 有用：

```bash
# 在该 agent 的 workspace/skills/ 中创建
cd ~/.openclaw/workspace-<agent-name>/skills
mkdir special-skill
# 创建 SKILL.md 和 scripts/

# 这个 skill 只对该 agent 可用
# 不会影响其他 agents
```

## 🎯 优先级规则

OpenClaw 按以下顺序查找 skills：

1. **Agent workspace** (`~/.openclaw/workspace-<agent>/skills/`) - 最高优先级
2. **全局目录** (`~/.openclaw/skills-global/`) - 中等优先级
3. **内置 skills** (OpenClaw bundled) - 最低优先级

这意味着：
- 如果 agent workspace 有同名 skill，优先使用它
- 否则使用 skills-global 中的版本
- 最后才使用 OpenClaw 内置的版本

## ✅ 优点

1. **单一来源** - 所有 skills 只维护一份
2. **自动同步** - 所有 agents 自动获得更新
3. **简化管理** - 只需在一个地方添加/更新/删除
4. **节省空间** - 不再重复存储
5. **避免冲突** - 不会有版本不一致的问题
6. **灵活性** - 仍可为特定 agent 创建专用 skills

## 🔄 自动化

### Skills 会自动更新

- `watch: true` 配置启用了文件监控
- 修改 skill 后，OpenClaw 自动检测
- 下次对话时自动使用新版本
- 无需手动重启 Gateway

### 新 Agent 自动获得所有 Skills

创建新 agent 时：
```bash
# 新 agent 自动继承所有 skills-global 中的 skills
# 无需额外配置
```

## 📋 维护清单

### 定期检查

```bash
# 查看所有 skills
ls ~/.openclaw/skills-global/

# 查看 OpenClaw 识别的 skills
openclaw skills list

# 检查 skills 状态
openclaw skills list | grep "ready"
```

### 清理无用的 Skills

```bash
# 删除不再使用的 skills
cd ~/.openclaw/skills-global
rm -rf <unused-skill>
```

### 备份

```bash
# 定期备份 skills-global
tar -czf skills-global-backup-$(date +%Y%m%d).tar.gz ~/.openclaw/skills-global/
```

## 🎉 总结

**现在的配置：**
- ✅ 29 个 skills 统一管理
- ✅ 所有 agents 共享同一套 skills
- ✅ 添加新 skill 只需在一个地方
- ✅ 更新 skill 所有 agents 自动生效
- ✅ 自动监控文件变化
- ✅ 支持 agent 特定的 skills

**后续操作：**
- 所有新 skills 添加到 `~/.openclaw/skills-global/`
- 所有 agents (包括未来创建的) 都会自动使用
- 维护简单，只需管理一个目录

**位置：** `~/.openclaw/skills-global/`
