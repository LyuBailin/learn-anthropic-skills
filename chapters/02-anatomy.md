# 第 2 章 · 文件解剖：SKILL.md 完整解读

> 读完这一章你应该能：① 手写一个符合规范的 `SKILL.md`；② 知道每个 frontmatter 字段的作用和推荐写法；③ 设计合理的目录结构组织附件。

---

## 2.1 一个最简 Skill

三步创建一个最简 skill：

```bash
mkdir -p ~/.claude/skills/hello-skill
```

```bash
cat > ~/.claude/skills/hello-skill/SKILL.md << 'EOF'
---
name: hello-skill
description: |
  当用户问候、说"hi"、"hello"、或希望跟 Claude 打个招呼时使用。
  此 skill 教 Claude 用一种温暖、有趣的方式回应问候。
---

# Hello Skill

## 回应规则

1. 第一次跟用户打招呼：热情、简短、说明你能帮什么
2. 已经有上下文：直接回应问候 + 提示上一次在做什么
3. 用户名字已知：用名字打招呼

## 风格要求

- 用 1-2 句话
- 不要堆砌"我是 AI，我能帮你……"这种自我介绍
- 匹配用户的语言（中文用户用中文）
EOF
```

重启 Claude Code，输入 "hi"，会看到这个 skill 触发。

---

## 2.2 SKILL.md 的两段式结构

一个 SKILL.md 由**两段**组成：

```
┌─────────────────────────────────────────┐
│                                         │
│  ---                                    │
│  YAML frontmatter                       │
│  name, description, when_to_use, ...    │
│  ---                                    │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  Markdown 主体                          │
│  # 标题                                 │
│  ## 工作流程                            │
│  ## 决策点                              │
│  ## 检查清单                            │
│  ...                                    │
│                                         │
└─────────────────────────────────────────┘
```

**YAML frontmatter**：机器读的元数据，决定**是否加载 / 怎么加载 / 加载到哪**。
**Markdown 主体**：Claude 读的工作流指令，决定**怎么干活**。

---

## 2.3 YAML Frontmatter 字段完整参考

### 2.3.1 必填字段

#### `name`（必填）

- **类型**：字符串
- **规则**：小写字母、数字、连字符；**≤ 64 字符**
- **作用**：Skill 唯一标识符，也是 `/skill-name` 命令名
- **注意**：跟目录名一致最佳，但 YAML 里必须显式写

```yaml
name: pdf-form-filler         # ✅ 正确
name: PDFFormFiller            # ❌ 不允许大写
name: pdf-form-filler-v2       # ⚠️ 允许但不推荐（版本进别的字段管）
```

#### `description`（必填）

- **类型**：字符串（多行可用 `|` 或 `>` 块）
- **作用**：Claude 用来判断**是否应该触发**这个 skill 的**唯一依据**
- **限制**：建议 ≤ 1024 字符；和 `when_to_use` 合计 ≤ 1536 字符
- **写法**：
  - **包含触发关键词**（用户大概率会说的词）
  - **包含应用场景**（具体在什么情况下用）
  - **不要泛化**（避免误触发）

```yaml
# ❌ 太弱：description 啥也没说
description: Generates documents.

# ❌ 太泛：什么文档都触发
description: Handles all document-related requests.

# ✅ 精确：覆盖目标场景 + 包含关键词
description: |
  从 Markdown 或结构化数据（JSON/CSV）生成专业 PDF 文档。
  当用户要求"创建 PDF"、"导出报告"、"生成发票"或"导出简历"时使用——
  即使他们没明确说"PDF"也应触发。
```

### 2.3.2 推荐字段

#### `when_to_use`

- **类型**：字符串（自然语言）
- **作用**：补充 description，提供更详细的触发场景
- **写法**：
  - 用**完整句子**描述使用场景
  - 可以包含"什么时候**不**用"
  - 可以用"用户会怎么说"的真实话术

```yaml
when_to_use: |
  Use this skill when the user wants to convert existing content
  (markdown files, structured data, or text) into a formatted PDF
  document. This includes reports, invoices, certificates, and resumes.
  Do NOT use this skill when the user just wants to read a PDF
  (use the document reading skill instead) or when the output
  should be a Word document.
```

> **重要**：**不要用关键词列表**（如 `triggers: [PDF, 文档, 报告]`）。Anthropic 明确建议用**自然语言**描述，让模型语义理解。

#### `paths`

- **类型**：字符串数组（glob 模式）
- **作用**：限定 Skill 只在涉及**特定文件**的对话中考虑触发
- **常见用法**：
  - 限定到特定语言（`*.ts`, `*.tsx`）
  - 限定到特定目录（`src/api/**`）
  - 限定到特定项目（`!docs/**` 排除）

```yaml
paths:
  - "src/**/*.ts"
  - "src/**/*.tsx"
  - "tests/**/*.test.ts"
```

**匹配规则**：
- 匹配"对话上下文中涉及的所有文件"（用户提及、Claude 读、Claude 写）
- 不是匹配"用户当前正在编辑的文件"
- 多个 pattern 之间是**或**关系

### 2.3.3 调用控制字段

#### `disable-model-invocation`

- **类型**：布尔
- **默认值**：`false`
- **作用**：**只允许用户手动触发**，禁止 Claude 自动调用

```yaml
disable-model-invocation: true
```

**使用场景**：
- 危险操作（部署、删数据、推送代码）
- 慢操作（跑全套测试、生成大报告）
- 显式触发的工具（"我想用 /review"）

**影响**：
- 用户的 `/skill-name` 命令**仍然有效**
- Claude **不会**自动调用
- description **也不会**注入到 system prompt（节省 token）

#### `user-invocable`

- **类型**：布尔
- **默认值**：`true`
- **作用**：**只允许 Claude 触发**，不出现在 `/` 命令菜单

```yaml
user-invocable: false
```

**使用场景**：
- 背景知识类 skill（领域术语表、API 参考）
- 不希望用户主动调用的辅助性能力

#### `argument-hint`

- **类型**：字符串
- **作用**：`/skill-name` 命令的参数补全提示
- **示例**：

```yaml
argument-hint: "[file-path] [severity]"
```

用户输入 `/review` 时，会显示提示：`/review [file-path] [severity]`

### 2.3.4 工具与执行控制

#### `allowed-tools`

- **类型**：字符串数组
- **作用**：Skill 激活期间**允许使用的工具白名单**
- **好处**：
  - Skill 期间**无需逐次授权**（提高效率）
  - 限制 Skill 能力边界（安全）

```yaml
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git diff *)
  - Bash(git log *)
```

**语法**：
- 工具名：`Read`, `Write`, `Edit`, `Bash`, `Grep`, `Glob`, `WebFetch`, `WebSearch`
- 带模式的 Bash：`Bash(npm run *)` 只允许 npm 脚本
- **不带通配符**：`Bash(git)` 允许任何 git 命令
- **默认**：继承父级所有工具（不加此字段 = 全部可用）

#### `model`

- **类型**：字符串
- **作用**：Skill 激活时**覆盖使用的模型**
- **取值**：`sonnet` `opus` `haiku` 或完整模型 ID

```yaml
model: opus  # 这个 skill 强制用 opus（哪怕主对话用 sonnet）
```

**使用场景**：
- 复杂推理 skill（架构设计、深度代码审查）→ opus
- 快速分类 skill（标签、提取）→ haiku
- 节省成本（默认 sonnet 的 skill 改成 haiku）

#### `effort`

- **类型**：字符串
- **取值**：`low` `medium` `high` `max`（仅 Opus 4.6+）
- **作用**：控制思考深度

#### `context: fork`

- **类型**：布尔 / 字符串
- **作用**：让 Skill **在 subagent 隔离上下文中运行**
- **取值**：
  - `context: fork` 简单布尔
  - `context: fork` + `agent: Explore` 指定 agent 类型

```yaml
context: fork
agent: Explore   # 可选：Explore / Plan / general-purpose
```

**效果**：
- Skill 内容加载到**全新的 subagent 上下文**
- 不携带主对话历史（节省 token）
- 适合"读大量文件做分析"的场景

#### `agent`

- **类型**：字符串
- **作用**：与 `context: fork` 配合，指定 subagent 类型
- **内置类型**：
  - `Explore`（Haiku，只读工具）—— 代码库搜索
  - `Plan`（继承，只读工具）—— 计划模式
  - `general-purpose`（继承，全部工具）—— 复杂任务

### 2.3.5 路径与环境

#### `shell`

- **类型**：字符串
- **取值**：`bash`（默认）`powershell`
- **作用**：指定 `!`command`` 动态注入使用的 shell

#### `hooks`

- **类型**：对象
- **作用**：Skill 生命周期钩子
- **示例**：

```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./validate.sh"
```

---

## 2.4 Markdown 主体怎么写

主体是 Claude 真正读的指令，写法没有强规范，但**有最佳实践**。

### 2.4.1 推荐结构

```markdown
# Skill 标题

简短介绍：这个 skill 干什么、解决什么问题。

## 工作流程

1. 第一步做什么
2. 第二步做什么
3. ...

## 关键决策点

- 遇到 X 情况 → 选择 A
- 遇到 Y 情况 → 选择 B

## 检查清单

- [ ] 完成度检查
- [ ] 质量检查
- [ ] 安全检查

## 输出格式

期望的输出长这样：

```json
{
  "status": "ok",
  "result": "..."
}
```

## 常见问题

**Q: 用户问 X 怎么办？**
A: 回答...

## 相关资源

- 详细配置见 [configuration.md](configuration.md)
- 示例见 [examples/](examples/)
```

### 2.4.2 引用资源文件

主体里**可以引用**同目录下的其他文件。Claude 会被引导去读这些文件。

```markdown
## 详细配置

完整的配置选项见 [configuration.md](configuration.md)。

## 表单填写细节

填写 PDF 表单的步骤详见 [forms.md](forms.md)。
```

**关键**：**所有引用的文件**必须和 `SKILL.md` 在**同一目录**或子目录。

### 2.4.3 大小建议

- **主体** < 500 行
- 如果超过 → 拆分成多个 `.md` 文件，主体做"目录页"
- **description + when_to_use** 合计 ≤ 1536 字符

### 2.4.4 解释 Why 而非堆砌 MUST

```markdown
# ❌ 堆砌 MUST
## 必须在生成 PDF 前先安装依赖
## 必须先检查用户输入是否合法
## 必须输出 JSON 格式

# ✅ 解释 Why
## 快速开始

首次使用需要安装依赖（fpdf2 库），否则脚本会报
ModuleNotFoundError。

## 输入校验

在处理前先检查用户输入，校验失败会让脚本崩溃且很难调试。
检查项包括：必填字段、字段类型、值域。

## 输出格式

输出 JSON 便于后续处理。如果输出非 JSON，下游脚本无法解析。
```

Claude 足够聪明，给它**理由**比给它**规则**更有效。

---

## 2.5 完整目录结构

### 2.5.1 最小结构

```
my-skill/
└── SKILL.md
```

### 2.5.2 典型结构

```
pdf-form-filler/
├── SKILL.md              # 入口：YAML + 工作流
├── scripts/              # 可执行脚本
│   ├── extract_fields.py
│   ├── fill_pdf.py
│   └── validate.py
├── references/           # 参考文档
│   ├── forms.md          # 表单填写细节
│   └── api.md            # 用到的库 API
├── assets/               # 静态资源
│   ├── template.pdf
│   └── fonts/
└── LICENSE.txt
```

### 2.5.3 多层结构

```
complex-skill/
├── SKILL.md              # 入口
├── configuration.md      # 配置相关
├── troubleshooting.md    # 排错
├── examples/             # 示例集合
│   ├── basic.md
│   ├── advanced.md
│   └── edge-cases.md
├── scripts/              # 工具脚本
│   ├── setup.sh
│   ├── run.py
│   └── validate.sh
└── integration/          # 集成相关
    ├── ci-cd.md
    └── api-clients.md
```

**原则**：
- **每个文件/目录的命名都要"自文档化"**——Claude 看到文件名就知道里面是什么
- **不要过深**——超过 3 层就难维护
- **同类型内容放一起**——所有 `examples/` 放示例，所有 `scripts/` 放脚本

### 2.5.4 文件名即导航信号

文件名是 Claude 理解内容的关键线索：

| 文件名 | 暗示 |
|--------|------|
| `basic-setup.md` | 入门内容 |
| `advanced-config.md` | 高级配置 |
| `emergency-recovery.sh` | 紧急恢复 |
| `troubleshooting.md` | 排错 |
| `examples.md` | 示例 |

---

## 2.6 YAML 常见错误

### 错误 1：YAML 缩进错误

```yaml
# ❌ 缩进不一致
allowed-tools:
- Read
  - Grep    # 这行多了 2 空格
- Glob

# ✅ 统一缩进
allowed-tools:
  - Read
  - Grep
  - Glob
```

### 错误 2：多行字符串符号

```yaml
# ❌ description 里有冒号 / 特殊字符没引号
description: Use when: PDF, forms

# ✅ 用 | 块或引号包裹
description: |
  Use when: PDF, forms, document generation.
```

### 错误 3：必填字段缺失

```yaml
# ❌ 缺 name
---
description: "..."
---

# ❌ 缺 description
---
name: my-skill
---
```

### 错误 4：name 命名违规

```yaml
# ❌ 大写
name: MySkill

# ❌ 包含下划线
name: my_skill

# ❌ 太长
name: this-is-a-very-long-skill-name-that-exceeds-the-sixty-four-character-limit

# ✅ 正确
name: my-skill
```

---

## 2.7 完整示例

下面是一个真实的 skill 文件，可直接复制使用：

```yaml
---
name: code-review
description: |
  审查代码改动，识别安全漏洞、命名问题、测试覆盖、性能问题。
  当用户说"review"、"审查"、"看看这个改动"、"code review"时使用。
  适用于任何 Git 仓库中的代码变更（已 staged 或 working tree）。
when_to_use: |
  Use this skill when the user has made code changes and wants
  feedback before committing or opening a PR. The skill performs
  a security-first review with checks for: hardcoded secrets,
  SQL injection, XSS, error handling, test coverage, and naming.
paths:
  - "src/**/*"
  - "lib/**/*"
  - "tests/**/*"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git diff *)
  - Bash(git log *)
  - Bash(git status)
argument-hint: "[optional: file-path]"
---

# Code Review Skill

## 工作流程

### 1. 收集变更上下文

先获取当前 Git 状态和 diff：

```bash
git status
git diff HEAD
git diff --staged
```

如果有未追踪的新文件，列出它们但**不读全文**——只读相关部分。

### 2. 分类审查

按以下顺序检查（严重程度从高到低）：

#### 🔴 严重问题（必须修复）

- **安全漏洞**
  - 硬编码的密码 / API key / token
  - SQL 拼接（注入风险）
  - 不安全的反序列化
  - 路径遍历（`..` / `~` 处理）
  - XSS（innerHTML 拼接未转义）
- **数据丢失风险**
  - 删除文件前未确认
  - 数据库操作无事务
  - 错误处理吞掉异常

#### 🟡 建议改进

- **代码质量**
  - 函数超过 50 行
  - 嵌套超过 3 层
  - 命名不清（a, tmp, data 这种）
  - 重复代码
- **错误处理**
  - catch 块为空
  - 错误消息泄露内部细节
- **性能**
  - N+1 查询
  - 不必要的同步循环
  - 大列表未分页

#### 🟢 亮点（值得肯定）

- 测试覆盖了边界条件
- 错误处理完善
- 命名清晰
- 注释解释"为什么"而非"做什么"

### 3. 输出格式

```markdown
## 审查结果

### 🔴 严重问题
- [问题描述] — 文件:行号 — 修复建议

### 🟡 建议改进
- [问题描述] — 文件:行号 — 修复建议

### 🟢 亮点
- [值得肯定的地方]

### 📊 统计
- 审查文件：N
- 严重问题：N
- 建议改进：N
```

## 关键决策点

- **变更太大**（> 500 行）→ 建议拆成多个 PR，只审查本次提交的
- **缺测试** → 在"建议改进"中标注，不强制要求
- **用户明确说"随便看看"** → 跳过严重问题检查，只做风格建议
- **涉及第三方库源码** → 不审查（只审查业务代码）

## 完整检查清单

- [ ] 没有硬编码 secret
- [ ] 没有 SQL 注入
- [ ] 没有 XSS
- [ ] 函数 ≤ 50 行
- [ ] 嵌套 ≤ 3 层
- [ ] 命名有意义
- [ ] 错误处理完善
- [ ] 关键路径有测试
- [ ] 没有 N+1 查询
- [ ] 没有内存泄漏

## 相关资源

- 详细审查规范见 [review-standards.md](review-standards.md)
- 常见问题案例见 [examples/](examples/)
```

---

## 2.8 接下来

- 想搞懂"这个 SKILL.md 是怎么被加载的" → [第 3 章 · 加载机制](./03-loading.md)
- 想直接动手写一个 → [第 4 章 · 实战编写](./04-writing.md)
- 想查 frontmatter 速查表 → 看 [`site/index.html`](../site/index.html)
