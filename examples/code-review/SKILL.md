---
name: code-review
description: |
  审查 Git 工作区和已 staged 的代码变更。按安全、命名、测试、性能四维度检查。
  当用户说"review 我的代码"、"审查改动"、"看看这个 PR"、"code review"时使用。
  输出结构化的严重问题、建议、亮点三个级别。
when_to_use: |
  Use this skill when the user has uncommitted changes (in working tree
  or staged) and wants feedback. Don't use for: explaining how code works,
  or generating new code.
paths:
  - "src/**/*"
  - "lib/**/*"
  - "app/**/*"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.py"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git diff *)
  - Bash(git log *)
  - Bash(git status)
  - Bash(git show *)
argument-hint: "[optional: base-branch]"
---

# Code Review Skill

详细文档见 [SKILL.md](../../chapters/04-writing.md#42-code-review代码审查)

## 工作流程

### Step 1：收集变更

```bash
git status
git diff HEAD
git diff --stat HEAD
```

### Step 2：分类审查

按严重度从高到低：

#### 🔴 P0：安全问题（必须修复）

- 硬编码的 secret（API key、密码、token、private key）
- SQL 注入风险（字符串拼接 SQL）
- 命令注入（`os.system(user_input)`）
- 路径遍历
- XSS
- 不安全的反序列化
- SSRF

#### 🟡 P1：建议改进

- 错误处理（catch 块为空、错误消息泄露内部细节）
- 资源泄漏
- 命名不清
- 函数过长（> 50 行）
- 嵌套过深（> 3 层）
- 重复代码
- 性能问题

#### 🟢 P2：亮点

- 测试覆盖了边界
- 错误处理完善
- 命名清晰有业务含义
- 注释解释"为什么"而非"做什么"
- 复用了已有工具
