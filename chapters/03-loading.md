# 第 3 章 · 加载机制：三层披露、token 经济性与触发决策

> 读完这一章你应该能：① 画出"用户发消息到 Claude 响应"整个数据流转图；② 算清不同 skill 数量的 token 占用；③ 知道怎么写 `description` 让触发更准。

---

## 3.1 端到端数据流

下面这张图展示了一条用户消息从进入到响应，**上下文窗口是怎么变化的**。

```
用户消息: "帮我把这个 PDF 表单填好"
              ↓
┌─────────────────────────────────────────────┐
│ 上下文窗口（初始状态）                       │
│                                              │
│  [System Prompt]                             │
│  ├─ Anthropic 基础提示                       │
│  ├─ 所有 Skill 的 name + description 列表   │  ← L1: 元数据层
│  └─ 当前会话上下文（如果有）                 │
│                                              │
│  [User Message]                              │
│  └─ "帮我把这个 PDF 表单填好"               │
│                                              │
│  [对话历史]（如有）                          │
└─────────────────────────────────────────────┘
              ↓
        Claude 决策: "这个任务匹配 pdf-form-filler"
              ↓
┌─────────────────────────────────────────────┐
│ 上下文窗口（触发后）                          │
│                                              │
│  [System Prompt]  同上                      │
│                                              │
│  [Tool Call: Read]                           │
│  └─ file_path: pdf-form-filler/SKILL.md     │
│                                              │
│  [Tool Result]  SKILL.md 完整内容加载        │  ← L2: 主体层
│                                              │
│  [User Message]                              │
│  └─ "帮我把这个 PDF 表单填好"               │
└─────────────────────────────────────────────┘
              ↓
        Claude 决策: "我需要表单字段信息"
              ↓
┌─────────────────────────────────────────────┐
│ 上下文窗口（深入加载）                        │
│                                              │
│  [前面所有内容]                               │
│                                              │
│  [Tool Call: Read]                           │
│  └─ file_path: pdf-form-filler/forms.md     │
│                                              │
│  [Tool Result]  forms.md 内容加载            │  ← L3: 资源层
└─────────────────────────────────────────────┘
              ↓
        Claude 决策: "需要执行 extract_fields.py"
              ↓
┌─────────────────────────────────────────────┐
│ 上下文窗口（执行工具）                        │
│                                              │
│  [前面所有内容]                               │
│                                              │
│  [Tool Call: Bash]                           │
│  └─ command: python extract_fields.py ...    │
│                                              │
│  [Tool Result]                               │
│  └─ stdout: 字段列表（脚本内容不进入上下文）  │  ← L3+: 代码执行
└─────────────────────────────────────────────┘
              ↓
        Claude 整理答案
              ↓
        响应用户
```

**几个关键点**：
- **脚本内容不进入上下文**——只跑、只拿结果
- **L1 元数据始终在**，L2/L3 跟着对话需要动态进出
- 每次 Read/Bash 工具调用都会**消耗 token**（不仅加载内容本身，还有工具调用的元信息）

---

## 3.2 token 经济性：装 100 个 skill 也只占 1 万词

### 3.2.1 数字演算

**假设场景**：
- 100 个 skill
- 每个 skill 的 description 平均 100 词
- 上下文窗口 200K token

**L1 元数据层**：
- 占用：`100 × 100 = 10,000 词 ≈ 13,000 token`
- 占窗口比：`13,000 / 200,000 = 6.5%`
- **可接受**

**单次 L2 加载**：
- 典型 SKILL.md 主体：~ 500 行 ≈ 2,000 词 ≈ 2,600 token
- 加载 1 个 skill：占窗口 1.3%
- 加载 5 个 skill（极端情况）：6.5%

**L3 资源按需加载**：
- 一次只读 1-2 个 reference
- 每个 reference：~ 500 词 ≈ 650 token
- 单次成本：~ 0.3%

### 3.2.2 对比：把所有内容都放 system prompt

| 方案 | 100 个 skill 的开销 |
|------|---------------------|
| 全部塞进 system prompt | 100 × 2000 词 = 200,000 词 = 直接撑爆 |
| 用 Skill 机制 | 13,000 词常驻 + 按需 2,600/次 |
| **节省** | **93%+** |

这就是为什么**Skill 不是"另一种写 system prompt 的方式"**——它是**让大规模知识/能力扩展成为可能**的关键设计。

### 3.2.3 token 节省的最佳实践

1. **description 控制在 100 词以内**
   - 太长 → 常驻开销大
   - 太短 → 触发不准
2. **主体控制在 500 行以内**
   - 超长 → 拆分成多个 reference
3. **reference 单文件控制在 200 行以内**
   - 超长 → 进一步拆
4. **脚本用代码而不是文档**
   - 脚本不进入上下文
   - 文档进入上下文

---

## 3.3 触发决策：Claude 怎么决定加载哪个 skill

### 3.3.1 决策流程

```
用户消息
   ↓
Claude 扫所有 L1 元数据（name + description + when_to_use + paths）
   ↓
对每个 skill 评估相关度
   ├─ 语义匹配？（向量相似度 / LLM 内部判断）
   ├─ paths 过滤？（涉及的文件是否匹配）
   └─ 调用控制约束？
        ├─ disable-model-invocation: true → 排除
        └─ user-invocable: false → 保留
   ↓
选择最相关的 1 个（或多个）
   ↓
调用 Read / Bash 工具加载 SKILL.md
   ↓
继续对话
```

### 3.3.2 description 的好坏直接影响触发

```yaml
# ❌ 太弱：Claude 经常不触发
description: Generates documents

# ❌ 太泛：什么请求都触发
description: Handles all document tasks

# ✅ 精准：覆盖目标 + 关键词
description: |
  从 Markdown 或结构化数据生成专业 PDF 文档。
  当用户说"创建 PDF"、"导出报告"、"生成发票"、"导出简历"时使用。
  即使用户没明确说"PDF"（只说"生成报告"），也应触发。
```

**写好 description 的 5 条规则**：

1. **包含用户大概率说的词**（关键词分析）
2. **包含应用场景**（不是"做什么"而是"什么时候用"）
3. **包含正向触发**（"X 时用"）
4. **包含负向不触发**（"Y 时不用"）
5. **控制在 100 词左右**

### 3.3.3 paths 字段的精确控制

`paths` 不只是"过滤"——它**改变 Claude 的判断权重**。

```yaml
paths:
  - "src/api/**/*.ts"
  - "src/api/**/*.js"
```

行为：
- 当对话涉及 `src/api/` 下的文件 → 这个 skill **优先考虑**
- 当对话不涉及 → 这个 skill **被排除**
- paths 不会出现在 system prompt 里，但它**影响 Claude 的内部决策**

**典型用法**：
- `*.test.ts` → 只在测试文件出现时触发的 skill
- `docs/**` → 只在文档相关时触发的 skill
- `!node_modules/**` → 显式排除

### 3.3.4 调用控制组合的精确行为

| 配置 | 用户可触发 | Claude 自动触发 | description 进上下文 |
|------|----------|----------------|---------------------|
| 默认 | ✓ | ✓ | ✓ |
| `disable-model-invocation: true` | ✓ | ✗ | ✗ |
| `user-invocable: false` | ✗ | ✓ | ✓ |

**节省 token 的技巧**：
- 如果 skill 只手动用 → `disable-model-invocation: true`（description 不进 L1）
- 如果 skill 只 Claude 用 → `user-invocable: false`（仍进 L1，但不出现在 `/` 菜单）
- 如果 skill 经常用 → 默认（进 L1）

### 3.3.5 多 skill 同时触发的处理

**场景**：装 5 个 skill，用户问"帮我看看这个 PR"。

**可能同时触发**：
- `code-review`（审查代码）
- `pr-summary`（总结 PR）
- `git-commit-helper`（生成提交信息）

**Claude 的处理**：
1. 评估每个的相关度
2. **不一定全部加载**——挑最相关的 1-2 个
3. 如果都需要 → 按顺序加载主体，逐个处理
4. 任务的输出可能用到多个 skill 的能力

**重要**：Claude **不会**自动并发加载多个 skill——它会**一个一个按顺序**读。

---

## 3.4 加载时机：什么时候进入上下文

### 3.4.1 L1（name + description）

**时机**：每次会话启动时一次性注入
**形式**：拼到 system prompt 末尾
**举例**：

```xml
<skills>
  <skill>
    <name>pdf-form-filler</name>
    <description>从 Markdown 或结构化数据生成专业 PDF 文档...</description>
  </skill>
  <skill>
    <name>code-review</name>
    <description>审查代码改动，识别安全漏洞...</description>
  </skill>
  ...
</skills>
```

**注意**：具体格式 Anthropic 没公开，但你可以假设是这个结构。

### 3.4.2 L2（SKILL.md 主体）

**时机**：Claude 判断相关后
**形式**：通过 Read 工具调用，把文件内容读入
**典型 token**：1,500 - 3,000 token

### 3.4.3 L3（资源文件）

**时机**：主体里有引用 OR Claude 主动需要
**形式**：Read 工具调用
**典型 token**：500 - 2,000 token / 文件

### 3.4.4 L3+（脚本执行）

**时机**：Claude 调用 Bash 工具时
**形式**：脚本内容**不进入**上下文，只执行拿结果
**典型 token**：仅 stdout/stderr 占用

---

## 3.5 触发决策的"内部黑盒"

**Anthropic 没有公开** Claude 内部到底用什么算法判断 skill 相关度。但根据社区观察和官方提示：

1. **不是简单的关键词匹配**——Claude 用 LLM 理解 description 的语义
2. **不是向量相似度**——`agentskills.io` 等社区方案做过实验，LLM 语义匹配比 embedding 检索更准
3. **会综合考虑**：description 内容 + when_to_use + paths 上下文 + 用户消息意图

**一个内部推断的伪代码**：

```python
def should_trigger_skill(user_message, available_skills):
    for skill in available_skills:
        # 1. paths 过滤
        if skill.paths and not file_in_paths(user_message.files, skill.paths):
            continue

        # 2. 调用控制约束
        if skill.disable_model_invocation:
            continue

        # 3. 语义匹配（用 LLM 内部判断）
        relevance = llm_judge_relevance(
            user_message.intent,
            skill.description,
            skill.when_to_use
        )

        if relevance > threshold:
            return skill

    return None
```

---

## 3.6 上下文窗口的"成长与压缩"

Claude Code（以及类似产品）的上下文窗口不是静态的：

```
┌─────────────────────────────────────────┐
│ 200K context window                      │
├─────────────────────────────────────────┤
│ [System Prompt]        静态 ~3K        │
│ [L1: All Skills]       静态 ~13K       │
│ [Tools Definitions]    静态 ~5K        │
│ [Conversation History] 动态增长         │
│ [Loaded Skills]        动态按需         │
│ [Tool Results]         动态累积         │
├─────────────────────────────────────────┤
│ 剩余可用                                │
└─────────────────────────────────────────┘
```

**自动压缩机制**：
- Claude Code 会**自动**在上下文快满时压缩
- 手动压缩：`/compact [focus]`
- 压缩会**总结**之前的对话历史，**不**卸载已加载的 skill

**最佳实践**：
- 用 `/context` 查看当前占用
- 用 `/clear` 清空对话（重新加载 L1）
- 长任务考虑用 `context: fork` 在 subagent 中跑

---

## 3.7 一个完整的 token 占用示例

**场景**：
- 装了 5 个 skill：pdf-form-filler, code-review, meeting-minutes, data-viz, git-commit
- 当前任务："帮我审查代码并生成提交信息"
- 触发了：code-review + git-commit

| 阶段 | 占用 | 说明 |
|------|------|------|
| 启动 | 13K | L1: 5 个 skill × 100 词 = 500 词 ≈ 650 token |
| + 工具定义 | 18K | 工具 schema 常驻 |
| + 用户消息 | 18.1K | "审查代码" ≈ 100 token |
| + code-review 主体 | 20.6K | 加载 SKILL.md ≈ 2,500 token |
| + git-commit 主体 | 23.1K | 加载 SKILL.md ≈ 2,500 token |
| + references | 25.0K | 按需加载 2 个 reference ≈ 1,900 token |
| + 对话历史 | 25.5K | 几个回合的对话 |
| + 工具结果 | 30.0K | git diff 输出等 |
| **剩余** | **170K** | 还有 85% 可用 |

**对比没有 skill**：
- 每次都要把"审查代码的规范"和"提交信息规范"粘贴进对话
- 占用可能 10K+（且**每次都重复**）
- 团队规范无法沉淀

---

## 3.8 性能优化：让加载更快

### 3.8.1 减少不必要的 L1 加载

```yaml
# 如果 skill 99% 都是手动调用
disable-model-invocation: true
# → 节省 ~100 词的常驻开销
```

### 3.8.2 减少 L2 加载

```markdown
# 主体 < 500 行
# 超过 → 拆分到 references/
```

### 3.8.3 减少 L3 加载

```markdown
# reference 引用明确
# 不要让 Claude 探索整个目录
```

### 3.8.4 用脚本代替文档

```python
# ❌ 在 SKILL.md 里写大段 SQL 拼接规则
# 每次都加载

# ✅ 写一个 validate_sql.py
# Claude 跑脚本，结果返回；脚本内容不加载
```

### 3.8.5 用 context: fork 隔离

```yaml
# 大量读文件的 skill 在 subagent 中跑
context: fork
agent: Explore
```

---

## 3.9 监控：怎么知道 skill 工作正不正常

### 3.9.1 Claude Code 内置命令

```bash
/context        # 查看当前上下文占用
/clear          # 清空对话，重新加载 L1
/cost           # 查看 token 消耗
/help           # 查看可用 skill 和命令
```

### 3.9.2 自检清单

- [ ] description 简洁（< 100 词）
- [ ] 主体精简（< 500 行）
- [ ] 引用结构清晰
- [ ] 用户实际触发率符合预期
- [ ] 没有误触发
- [ ] 加载后没溢出窗口

### 3.9.3 调试触发问题

| 现象 | 排查 |
|------|------|
| 完全不触发 | description 关键词；paths 是否过严；`disable-model-invocation` 是否误设 |
| 误触发 | description 太泛；加入负向触发描述 |
| 加载失败 | SKILL.md 格式错误；YAML 解析失败 |
| 加载后崩溃 | 主体太长撑爆窗口；reference 互相循环引用 |

详见 [第 8 章 · 调试与反模式](./08-debug.md)。

---

## 3.10 接下来

- 想动手写一个 → [第 4 章 · 实战编写](./04-writing.md)
- 想知道 API 怎么加载 skill → [第 5 章 · API 集成](./05-api.md)
- 触发不准想排查 → [第 8 章 · 调试与反模式](./08-debug.md)
