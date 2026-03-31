# Skill Manager - 使用指南

## ✅ 已创建

**skill-manager** 已添加到 `~/.openclaw/skills-global/`

所有 agents (boss, search, 以及未来的新 agents) 现在都可以使用这个 skill 来管理其他 skills！

## 📋 功能

### 1. 列出所有 Skills

```bash
node ~/.openclaw/skills-global/skill-manager/scripts/manager.js list
```

显示所有已安装的 skills 及其描述。

### 2. 添加新 Skill

#### 从 ClawHub 安装
```bash
node ~/.openclaw/skills-global/skill-manager/scripts/manager.js add --from clawhub --name <skill-name>
```

#### 从本地目录复制
```bash
node ~/.openclaw/skills-global/skill-manager/scripts/manager.js add --from local --path /path/to/skill
```

#### 从 Git 仓库克隆
```bash
node ~/.openclaw/skills-global/skill-manager/scripts/manager.js add --from git --url https://github.com/user/skill.git
```

#### 创建新 skill 模板
```bash
node ~/.openclaw/skills-global/skill-manager/scripts/manager.js add --from template --name my-new-skill
```

### 3. 删除 Skill

```bash
node ~/.openclaw/skills-global/skill-manager/scripts/manager.js remove --name <skill-name>
```

强制删除（不确认）：
```bash
node ~/.openclaw/skills-global/skill-manager/scripts/manager.js remove --name <skill-name> --force
```

### 4. 同步 Skills

```bash
# 清理重复的 skills
node ~/.openclaw/skills-global/skill-manager/scripts/manager.js sync

# 检查并修复 skills
node ~/.openclaw/skills-global/skill-manager/scripts/manager.js sync --fix
```

## 🎯 使用场景

### 场景 1: 安装新 Skill

**用户说：** "帮我安装一个天气查询的 skill"

**你的操作：**
```bash
node ~/.openclaw/skills-global/skill-manager/scripts/manager.js add --from clawhub --name weather
```

**结果：** 所有 agents 立即可以使用 weather skill

### 场景 2: 创建自定义 Skill

**用户说：** "我想创建一个自动化任务的 skill"

**你的操作：**
```bash
node ~/.openclaw/skills-global/skill-manager/scripts/manager.js add --from template --name task-automation
```

**结果：** 在 `~/.openclaw/skills-global/task-automation/` 创建了模板，用户可以编辑

### 场景 3: 查看所有 Skills

**用户说：** "我有哪些 skills？"

**你的操作：**
```bash
node ~/.openclaw/skills-global/skill-manager/scripts/manager.js list
```

**结果：** 显示所有 30 个 skills 及其描述

### 场景 4: 删除不用的 Skill

**用户说：** "删除 old-skill，我不用了"

**你的操作：**
```bash
node ~/.openclaw/skills-global/skill-manager/scripts/manager.js remove --name old-skill
```

**结果：** 所有 agents 不再能使用该 skill

## 🔄 自动化

### 所有操作自动对所有 Agents 生效

- ✅ 添加 skill → 所有 agents 立即可用
- ✅ 删除 skill → 所有 agents 立即不可用
- ✅ 修改 skill → 所有 agents 自动使用新版本
- ✅ 无需重启 Gateway（文件监控已启用）

### 工作原理

1. **全局目录：** 所有 skills 在 `~/.openclaw/skills-global/`
2. **OpenClaw 配置：** `skills.load.extraDirs = ["~/.openclaw/skills-global"]`
3. **文件监控：** `watch: true` 自动检测变化
4. **所有 agents 共享：** boss, search, 以及未来的新 agents

## 📊 当前状态

```
总共 30 个 skills:
- 29 个已有的 skills
- 1 个新增的 skill-manager

所有 skills 位置: ~/.openclaw/skills-global/
所有 agents 可用: ✅
```

## 💡 最佳实践

### 添加 Skill 时

1. **优先从 ClawHub 安装** - 已验证和测试
2. **使用模板创建新 skill** - 结构规范
3. **从 Git 克隆时检查来源** - 安全第一

### 删除 Skill 时

1. **先确认没有依赖** - 避免破坏其他 skills
2. **备份重要的 skills** - 防止误删
3. **使用确认提示** - 避免意外删除

### 维护 Skills

1. **定期运行 list** - 检查 skills 状态
2. **定期运行 sync** - 清理重复和修复问题
3. **定期备份** - `tar -czf skills-backup.tar.gz ~/.openclaw/skills-global/`

## 🎉 总结

**现在你可以：**

1. ✅ 通过 skill-manager 添加新 skills
2. ✅ 所有 agents 自动获得新 skills
3. ✅ 统一管理所有 skills
4. ✅ 不需要手动配置每个 agent

**后续添加 skill 的流程：**

```bash
# 1. 添加 skill
node ~/.openclaw/skills-global/skill-manager/scripts/manager.js add --from clawhub --name <skill-name>

# 2. 完成！所有 agents 自动可用
```

**就这么简单！** 🎊
