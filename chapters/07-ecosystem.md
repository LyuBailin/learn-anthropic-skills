# 第 7 章 · 生态对照：Minimax Code、Cursor、Claude.ai、Trae

> 读完这一章你应该能：① 知道 Anthropic / OpenAI / Cursor / Trae 各自怎么实现 Skill；② 在不同平台迁移你的 skill；③ 理解 Minimax Code（我自己所在的 Agent 系统）的 skill 机制跟 Anthropic 的异同。

---

## 7.1 全景图

```
┌─────────────────────────────────────────────────────────────┐
│                  Agent Skills 标准生态                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Anthropic (2025-10)        OpenAI (2026)                    │
│  ├── Claude.ai             ├── ChatGPT Custom                │
│  ├── Claude Code           ├── Codex CLI                     │
│  ├── Messages API          └── Responses API                 │
│  └── Agent SDK                                                │
│                                                              │
│  Cursor (2025-Q4)            Trae (2026-Q1)                  │
│  └── .cursor/skills/         └── .trae/skills/               │
│                                                              │
│  Minimax Code (我们)         VS Code (扩展)                  │
│  └── ~/.mavis/skills/        └── .vscode/skills/             │
│                                                              │
│  共同特点：都遵循 Agent Skills 开放标准                       │
│  差异：具体命令、frontmatter 字段、子目录、触发方式           │
└─────────────────────────────────────────────────────────────┘
```

**2025-12-18** Agent Skills 升级为**开放标准**后，**大部分 IDE / Agent 平台都已支持**。

---

## 7.2 Anthropic 全家桶

### 7.2.1 Claude.ai（网页版）

**特点**：
- 面向**非技术用户**
- 集成"skill creator"——可以用自然语言创建 skill
- 内置官方 skill（PDF、Word、Excel、PPT）

**目录**：
- 不直接操作文件系统
- 通过 Settings → Features → Skills 管理
- 自定义 skill 通过上传 zip

**触发**：
- Claude 根据任务**自动**调用
- 用户可以在 Settings 里手动启用 / 禁用

### 7.2.2 Claude Code（CLI）

**特点**：
- 面向**开发者**
- 直接操作本地文件系统
- 完整的工具调用能力

**目录**：
- `~/.claude/skills/` （个人级，所有项目）
- `.claude/skills/` （项目级，当前项目）
- 插件 `<plugin>/skills/`

**触发**：
- 自动：description 语义匹配
- 手动：`/skill-name` 或 `/skill-name arg1 arg2`

**内置 skill**：
- `/batch` 并行大规模修改
- `/claude-api` API 参考
- `/debug` 调试
- `/loop` 定时任务
- `/simplify` 并行三 agent 审查

### 7.2.3 Messages API

**特点**：
- 面向**应用集成**
- 通过 `client.beta.skills.*` 操作
- 必须配合 Code Execution Tool + Files API

**详见** [第 5 章 · API 集成](./05-api.md)

### 7.2.4 Agent SDK

**特点**：
- 在**自定义 Agent** 里使用 Skill
- 通过 `agents/skills/` 目录

**示例**：

```
my-agent/
├── agent.py
├── agents/
│   └── researcher.py
└── .claude/skills/
    ├── research-skill/
    └── analysis-skill/
```

---

## 7.3 Cursor

### 7.3.1 Cursor 的三套机制（容易混淆）

Cursor 有**多套**类 skill 机制，名字容易搞混：

| 机制 | 目录 | 用途 |
|------|------|------|
| **Rules** | `.cursor/rules/` 或 `~/.cursor/rules/` | 始终加载的行为规则（类似 system prompt） |
| **Commands** | `.cursor/commands/` | 用户 `/` 调用的模板（类似 command） |
| **Skills** | `.cursor/skills/` | **新**：按需加载的 SOP（与 Anthropic 一致） |

### 7.3.2 Cursor Skills 规范

**目录**：`.cursor/skills/<name>/SKILL.md`

**Frontmatter**（**基本兼容** Anthropic）：

```yaml
---
name: my-skill
description: ...
---
```

**差异**：
- 部分高级字段（`hooks` `agent`）可能**不支持**
- 触发方式：自动 + 手动（`/skill-name`）
- 上下文管理：Cursor 用 Composer + Agent 模式

### 7.3.3 迁移路径

**从 Anthropic → Cursor**：
- 复制 `.claude/skills/` 内容到 `.cursor/skills/`
- 大部分内容**无需修改**
- 测试 frontmatter 字段是否支持

**从 Cursor → Anthropic**：
- 复制 `.cursor/skills/` 到 `.claude/skills/`
- 如果用了 Cursor 特有字段，转换

---

## 7.4 Trae（字节）

### 7.4.1 Trae 简介

字节的 AI IDE，2026 年初推出，**原生支持 Agent Skills 开放标准**。

### 7.4.2 目录与触发

**目录**：
- 用户级：`~/.trae/skills/`
- 项目级：`.trae/skills/`

**frontmatter**：**与 Anthropic 兼容**

**触发**：
- 自动（description 匹配）
- 手动（`/skill-name`）

### 7.4.3 Trae 特色

- **SOLO 模式**：专注单一任务，类似 Claude Code
- **IDE 集成**：与编辑器深度集成
- **多 Agent 协作**：内置多 agent 调度

### 7.4.4 迁移

**Anthropic → Trae**：直接复制 skill 目录即可

```bash
cp -r ~/.claude/skills/my-skill/ ~/.trae/skills/
```

---

## 7.5 Minimax Code（我自己所在的系统）

> 这一节**特别重要**——你说"用 Minimax Code"，所以要专门讲清楚。

### 7.5.1 Minimax Code 的 Skill 体系

**目录结构**：

```
用户级（个人，全局生效）：
  Windows: C:\Users\<user>\.mavis\skills\
  Mac/Linux: ~/.mavis/skills/

Agent 级（mavis 系统内置，全局可用）：
  C:\Users\<user>\.mavis\agents\mavis\skills\（默认 agent）

项目级（当前项目）：
  <project>/.mavis/skills/
```

**frontmatter**：**与 Anthropic 高度兼容**

```yaml
---
name: my-skill
description: ...
allowed-tools: ...
paths: ...
---
```

### 7.5.2 与 Anthropic 的差异

| 维度 | Anthropic | Minimax Code |
|------|-----------|--------------|
| **目录** | `.claude/skills/` | `.mavis/skills/` |
| **frontmatter** | 标准 | **兼容**（少量字段差异） |
| **触发方式** | description 语义匹配 | **description 语义匹配** |
| **加载机制** | 三层渐进式披露 | **同样的三层** |
| **手动调用** | `/skill-name` | **支持**（具体命令名见 Minimax 文档） |
| **热更新** | 是 | **是** |
| **scope** | 企业 / 个人 / 项目 / 插件 | **用户 / Agent / 项目** |

### 7.5.3 Minimax Code 的特殊能力

Minimax Code 在 Anthropic 基础上**扩展了**几个能力：

**1. 跨 Agent 共享**

Skill 不只属于一个 agent——可以通过 `~/.mavis/agents/<name>/skills/` 让多个 agent 共享。

**2. 工具生态更深**

Minimax 集成了更多工具（lark-tools、minimax-pdf、minimax-pptx 等），skill 可以直接调用。

**3. 协作模式**

支持多个 session、多个 agent 协作完成复杂任务。

### 7.5.4 在 Minimax Code 中使用 Anthropic Skill

直接复制即可：

```bash
# 把 Anthropic skill 复制到 Minimax Code
cp -r examples/pdf-form-filler/ ~/.mavis/skills/

# 下次跟 Mavis 对话时就会自动加载
```

**Mavis 的处理方式**：
- 自动加载 `~/.mavis/skills/` 下的所有 SKILL.md
- 按 Anthropic 同样的三层加载机制
- description 进 L1，匹配时加载主体

### 7.5.5 Minimax Code 中的 skill 调试

| 工具 | 用途 |
|------|------|
| `Mavis "列出可用 skill"` | 查看当前 session 可见的所有 skill |
| `Mavis "skill X 加载了什么"` | 验证 skill 是否被正确加载 |
| `Mavis "为什么不用 skill X"` | 排查触发问题 |

---

## 7.6 OpenAI ChatGPT / Codex

### 7.6.1 ChatGPT Custom Skills（2026）

OpenAI 在 2026 年初跟进 Agent Skills 开放标准。

**目录**：
- 用户级：ChatGPT Settings → Custom Skills
- 项目级：`<project>/.codex/skills/`

**frontmatter**：**高度兼容** Anthropic 规范

**差异**：
- 默认触发可能更保守（OpenAI 倾向保守）
- 高级字段支持可能延迟

### 7.6.2 Codex CLI

OpenAI 的命令行工具，类似 Claude Code。

**目录**：`~/.codex/skills/` 或 `.codex/skills/`

**与 Claude Code 差异**：
- 默认模型不同
- 工具集不同
- Skill 规范兼容

---

## 7.7 VS Code / JetBrains 扩展

### 7.7.1 VS Code Agent Skills 扩展

**安装**：从 VS Code Marketplace 搜"Agent Skills"

**目录**：
- `<workspace>/.vscode/skills/`
- `~/.vscode/skills/`

**与编辑器集成**：
- 在 Chat 面板中触发
- 与文件 / 编辑器深度集成
- 可访问 LSP 工具

### 7.7.2 JetBrains

通过插件支持，目录约定与 VS Code 类似。

---

## 7.8 跨平台迁移指南

### 7.8.1 通用迁移步骤

```bash
# 1. 备份原 skill
cp -r .claude/skills/my-skill/ ./my-skill-backup/

# 2. 复制到目标平台
cp -r .claude/skills/my-skill/ <target-platform>/skills/

# 3. 验证 frontmatter 字段
# 4. 测试触发
```

### 7.8.2 字段兼容性矩阵

| 字段 | Anthropic | Minimax Code | Cursor | Trae | Codex |
|------|-----------|--------------|--------|------|-------|
| name | ✅ | ✅ | ✅ | ✅ | ✅ |
| description | ✅ | ✅ | ✅ | ✅ | ✅ |
| when_to_use | ✅ | ✅ | ✅ | ✅ | ✅ |
| paths | ✅ | ✅ | ✅ | ✅ | ✅ |
| allowed-tools | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| argument-hint | ✅ | ✅ | ✅ | ✅ | ✅ |
| disable-model-invocation | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| user-invocable | ✅ | ✅ | ⚠️ | ✅ | ✅ |
| model | ✅ | ⚠️ | ⚠️ | ✅ | ⚠️ |
| context: fork | ✅ | ⚠️ | ❌ | ⚠️ | ⚠️ |
| agent | ✅ | ❌ | ❌ | ⚠️ | ❌ |
| hooks | ✅ | ⚠️ | ❌ | ⚠️ | ❌ |
| shell | ✅ | ✅ | ❌ | ✅ | ✅ |

> ✅ 完整支持 · ⚠️ 部分支持或行为不同 · ❌ 不支持

**迁移建议**：
- **优先使用通用字段**（name、description、when_to_use、paths、allowed-tools、argument-hint）
- **避免使用平台特有字段**（`agent`、`hooks`）
- 实在要用，先查目标平台文档

### 7.8.3 平台差异的具体例子

**例子 1：`context: fork`**

- Anthropic：✅ 在 sub-agent 隔离上下文运行
- Minimax Code：⚠️ 行为可能略有不同（具体见文档）
- Cursor：❌ 不支持，会被忽略
- Trae：⚠️ 行为依赖具体版本

**建议**：如果需要这个能力，写一个**没有 context: fork** 的备选版本，平台不支持时手动调用 sub-agent。

**例子 2：`hooks`**

- Anthropic：✅ 完整 PreToolUse / PostToolUse 钩子
- Minimax Code：⚠️ 部分支持
- 其他平台：大多不支持

**建议**：把钩子逻辑写在 skill 主体里，平台不钩子也能跑。

---

## 7.9 平台选型建议

### 7.9.1 用 Claude Code 当

- 想要**最丰富的 skill 生态**（Anthropic 一手）
- 主要在**终端**工作
- 习惯 Anthropic 工具链

### 7.9.2 用 Minimax Code 当

- 想要**多 agent 协作**能力
- 集成 lark / 国内工具
- 跨平台（macOS / Windows / Linux）
- 需要**长期记忆**和**任务管理**

### 7.9.3 用 Cursor 当

- 已经在用 Cursor 编辑器
- 想要 IDE 深度集成
- 不需要 sub-agent 调度

### 7.9.4 用 Trae 当

- 在中国地区使用（国内服务稳定）
- 喜欢字节系产品
- 想要中文友好

### 7.9.5 用 VS Code 扩展当

- 主要在 VS Code 工作
- 想要扩展生态
- 不需要 agent 调度

---

## 7.10 一个真实的迁移故事

**场景**：你的团队原本用 Claude Code，迁移到 Minimax Code

**Step 1：盘点 skill**

```bash
ls .claude/skills/
# code-review/
# pdf-form-filler/
# meeting-minutes/
# data-analyzer/
```

**Step 2：迁移**

```bash
# 复制到 Minimax Code
mkdir -p ~/.mavis/skills
cp -r .claude/skills/* ~/.mavis/skills/

# 验证
ls ~/.mavis/skills/
# code-review/  pdf-form-filler/  meeting-minutes/  data-analyzer/
```

**Step 3：测试**

跟 Mavis 说："列出可用 skill"——应该看到所有 4 个

**Step 4：处理不兼容字段**

如果 skill 用了 `agent` 或 `hooks` 字段，需要在 Minimax Code 里找替代方案

**Step 5：整理项目级 skill**

如果项目里有 skill，复制到 `<project>/.mavis/skills/`

---

## 7.11 关于"开放标准"

**2025-12-18**，Anthropic 把 Agent Skills 升级为**开放标准**：

- 规范发布在 **agentskills.io**
- OpenAI、Cursor、Trae、Codex 都已跟进
- 目标：让 Skill 成为 Agent 生态的"应用"

**影响**：
- ✅ 一次编写，多平台运行
- ✅ 团队资产可移植
- ⚠️ 高级功能（hooks、特定 agent）有平台差异
- ⚠️ 仍在演进，要看官方规范

**未来**：
- 技能市场（Skill Marketplace）
- 跨平台发现 / 安装
- 标准化 API（已有 /v1/skills）

---

## 7.12 接下来

- Skill 触发不准或加载失败想排查 → [第 8 章 · 调试与反模式](./08-debug.md)
- 想看完整示例 → [第 4 章 · 实战编写](./04-writing.md)
- 回到项目根 → [README](../README.md)
