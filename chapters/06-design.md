# 第 6 章 · 体系设计：多 Skill 架构、版本管理、与 MCP 协同

> 读完这一章你应该能：① 设计一个**企业级**的 skill 体系；② 解决多 skill 冲突、命名空间、版本管理问题；③ 理解 skill / MCP / sub-agent 怎么协同；④ 监控 skill 体系的健康度。

---

## 6.1 为什么需要"体系设计"

单 skill 简单，**多 skill 协作**才是工程化。

真实场景中你会遇到：

| 问题 | 表现 |
|------|------|
| **数量爆炸** | 团队 50 个 skill，常驻 token 占满 |
| **职责重叠** | 两个 skill 都"审查代码"，触发混乱 |
| **命名冲突** | 个人和项目同名 skill，谁优先？ |
| **版本错乱** | A 用 v1、B 用 v2，行为不一致 |
| **加载失败** | 一个 skill 写错，Claude 不响应 |
| **可观测性** | 不知道哪些 skill 经常触发、哪些从不触发 |
| **安全审计** | 谁装的 skill？skill 里有恶意脚本？ |

**体系设计** = 解决这些问题的工程方法。

---

## 6.2 命名空间与作用域设计

### 6.2.1 四级作用域（按优先级）

```
企业（最高）> 个人 > 项目 > 插件（最低）
```

- **企业级**：通过 Managed Settings 部署，组织全员可见
- **个人级**：`~/.claude/skills/`（Mac/Linux）或 `%USERPROFILE%\.claude\skills\`（Windows）
- **项目级**：`.claude/skills/`，可 git 追踪，团队共享
- **插件级**：`<plugin>/skills/`，命名空间隔离 `plugin-name:skill-name`

### 6.2.2 命名约定

**原则**：避免冲突、含义清晰、易搜索

```
# ❌ 不推荐
my-skill
test
new
skill1

# ✅ 推荐：领域-功能-版本（可选）
data-pipeline-etl
api-doc-generator
react-component-review
security-vuln-scanner
pdf-form-filler-v2   # 版本用单独字段管
```

**命名规则**：
- 小写字母 + 数字 + 连字符
- 避免下划线、点、空格
- 长度 ≤ 64 字符
- 体现**领域**（pdf、api、data、test、deploy）+ **功能**（form-filler、review、generator）

### 6.2.3 命名空间隔离

当多个 skill 名字相同时：
- **企业** > **个人** > **项目** > **插件**
- 插件用 `<plugin-name>:<skill-name>` 避免冲突
- **不建议**依赖优先级掩盖冲突——应该**改名**或**合并**

```yaml
# 插件内的 skill 引用
---
name: review
description: ...
---
# 通过 plugin:review 引用
```

---

## 6.3 多 Skill 协同模式

### 6.3.1 串行：链式触发

**场景**：A skill 输出 → B skill 接着处理

```
用户问 → [skill-A: 数据分析] → 结果
                    ↓
           [skill-B: 生成报告] → 最终输出
```

**实现方式**：

- 显式：A skill 主体里写"完成 X 后调用 /skill-B"
- 隐式：Claude 自动判断下一步用哪个 skill

**示例**：

```yaml
# skill-A: data-analyzer
description: 分析 CSV/JSON 数据，输出统计结果
when_to_use: 当用户提供数据文件希望分析时

# skill-B: report-generator
description: 把分析结果生成 PDF/HTML 报告
when_to_use: 当有结构化分析结果希望输出报告时
```

用户："分析这份数据并生成报告"
→ data-analyzer 触发 → 输出 JSON
→ report-generator 接着触发 → 输出 PDF

### 6.3.2 并行：多 skill 独立

**场景**：多 skill 同时处理一个任务的不同方面

```
用户问 → Claude 同时触发：
       ├─ [skill-A: 安全审查]
       ├─ [skill-B: 性能审查]
       └─ [skill-C: 风格审查]
                    ↓
           Claude 整合结果
```

**实现方式**：Claude 内部决策，一次加载多个 skill 主体

**注意**：
- **不**适合"互相依赖"的 skill（应该串行）
- 适合"独立可并行"的检查项
- 注意 token 占用（5 个 skill 同时加载 = 5 × 3K = 15K）

### 6.3.3 分层：基础 + 扩展

**场景**：一个"基础 skill"做通用事，多个"扩展 skill"做专门事

```
base-skill: code-review-base
  - 通用审查流程
  - 调用者：所有 review 类 skill

ext-skill: code-review-security (继承自 base)
ext-skill: code-review-performance (继承自 base)
ext-skill: code-review-style (继承自 base)
```

**实现方式**：在子 skill 主体里明确引用 base

```yaml
# code-review-security
---
name: code-review-security
description: 专注安全维度的代码审查（SQL 注入、XSS、SSRF）
when_to_use: 当用户特别要求"安全审查"时
---

# Code Review — Security

## 前置

先按 `code-review-base` 的流程收集变更。

## 重点检查

只关注安全问题（详见 references/security-checklist.md）：

1. 注入类漏洞
2. 敏感数据
3. 加密认证
4. ...

## 输出

只输出 🔴 严重问题（安全相关），其他维度不输出。
```

### 6.3.4 互斥：避免同时触发

**场景**：两个 skill 职责不重叠，但用户输入可能模糊

```
A skill: doc-writer (写文档)
B skill: doc-reader (读文档)
```

**问题**：用户说"看一下这个文档"——Claude 该用 reader 还是 writer？

**解决方案**：

```yaml
# doc-writer
description: |
  创建新文档（从模板生成 Word / Markdown / HTML）。
  当用户说"写文档"、"生成报告"、"创建 README"时使用。
  不要用于：阅读 / 总结现有文档（用 doc-reader）。

# doc-reader
description: |
  阅读并总结现有文档。
  当用户说"看看这个文档"、"总结 PDF"、"读一下 README"时使用。
  不要用于：创建新文档（用 doc-writer）。
```

**互斥规则**：
- 在 description 里**显式**说明"不用于 X"
- 用 when_to_use 加强区分
- 实在分不清就让用户选

---

## 6.4 版本管理

### 6.4.1 版本化的必要性

**场景**：一个 skill 在生产中用着好好的，你想加个新功能

- **直接改 SKILL.md** → 所有用户立刻拿到新版本
- **风险**：新版本有 bug → 全员影响
- **解决**：版本化

### 6.4.2 Anthropic Skills API 的版本管理

```python
# 第一次上传
skill_v1 = client.beta.skills.create(
    name="pdf-form-filler",
    skill_data=open("v1.zip", "rb"),
    betas=BETAS
)
# → skill_id, version=1

# 改了之后第二次上传
skill_v2 = client.beta.skills.create(
    name="pdf-form-filler",
    skill_data=open("v2.zip", "rb"),
    betas=BETAS
)
# → 同 skill_id, version=2
```

**调用时指定版本**：

```python
# 用最新版
{"type": "custom", "skill_id": skill_id, "version": "latest"}

# 用指定版
{"type": "custom", "skill_id": skill_id, "version": "2"}
```

### 6.4.3 客户端的版本策略

**Claude Code / Claude.ai**：默认总是用最新版

**API 用户**：可以选择"latest"或锁定版本

**建议**：
- 开发环境：使用 `latest`
- 生产环境：**锁定版本号**，灰度发布
- 升级时：先在测试环境验证，再更新生产

### 6.4.4 文件级 vs 包级版本

**文件级**：在 `SKILL.md` frontmatter 里加 `version` 字段

```yaml
---
name: pdf-form-filler
version: 1.2.0
description: ...
---
```

**包级**：通过 Skills API 的版本号管理（生产推荐）

---

## 6.5 与 MCP 的协同设计

### 6.5.1 Skill 和 MCP 的本质区别

| 维度 | Skill | MCP Server |
|------|-------|-----------|
| **本质** | 静态指令 + 脚本 | 动态运行的工具服务 |
| **加载** | 按需（静态文件） | 连接时加载（持续运行） |
| **能力** | 教 AI 做事 | 给 AI 工具 |
| **状态** | 无 | 有（持续运行的进程） |
| **网络** | 无（脚本本地跑） | 需要 server |

**经典比喻**：
- **Skill = 操作手册 + 工具箱**（纸 + 锅）
- **MCP = 外部供应商**（供应商接进来了）

### 6.5.2 Skill 调用 MCP

**场景**：Skill 需要外部数据

```yaml
# skill: data-report
description: 生成数据报告，需要从 Notion / DB 拉数据

# 实际工作流：
# 1. Claude 加载这个 skill
# 2. Skill 主体说："用 notion MCP 拉取页面 X"
# 3. Claude 调用 MCP 工具
# 4. 拿到数据后用 skill 里的脚本生成报告
```

**SKILL.md 主体**：

```markdown
## 工作流程

### Step 1: 拉取数据

用 Notion MCP 拉取指定页面的内容：
- 调用 `mcp__notion__get_page` 获取页面
- 调用 `mcp__notion__get_block_children` 获取内容块

### Step 2: 处理数据

用本地的 `scripts/analyze.py` 处理...

### Step 3: 生成报告

调用 `mcp__notion__create_page` 写回新页面
```

### 6.5.3 MCP 提供能力，Skill 提供流程

**经典组合**：

| 任务 | MCP（工具） | Skill（流程） |
|------|------------|---------------|
| 客服数据查询 | `notion` / `slack` MCP | "客服应答流程" skill |
| 财务报告 | 数据库 MCP | "月报生成" skill |
| CI/CD | `github` MCP | "部署流程" skill |
| 文件操作 | `filesystem` MCP | "PDF 填表" skill |

**原则**：
- **MCP 负责"能连上"**——给 AI 工具
- **Skill 负责"会做"**——给 AI 流程

### 6.5.4 何时用 Skill、何时用 MCP

**用 Skill**：
- 流程是**固定的**（SOP）
- 不需要外部实时数据
- 团队内部知识沉淀

**用 MCP**：
- 需要**实时**外部数据
- 需要**精确调用**外部 API
- 不同任务需要不同工具组合

**两者结合**：
- 复杂工作流：Skill 给流程 + MCP 给工具
- 简单查询：只用 MCP
- 团队规范：只用 Skill

---

## 6.6 与 Sub-agent 的协同设计

### 6.6.1 Skill 和 Sub-agent 的本质区别

| 维度 | Skill | Sub-agent |
|------|-------|-----------|
| **本质** | 函数 / 工具 | LLM 实例 |
| **是否需要 LLM** | ❌ | ✅ |
| **状态** | 无 | 有（独立上下文） |
| **推理能力** | ❌ | ✅ |
| **Token 成本** | 低（无 LLM 调用） | 高（独立 LLM 调用） |

### 6.6.2 Skill 调 Sub-agent：`context: fork`

```yaml
---
name: deep-research
description: 深度研究某个主题
context: fork
agent: general-purpose
---

# Deep Research

## 工作流程

在 subagent 隔离上下文中执行：

1. 读 5-10 个相关文件
2. 搜索网络资料
3. 综合分析
4. 输出研究报告
```

**效果**：
- 主体被加载到**新的 subagent 上下文**
- 不污染主对话
- 适合"大量读文件"的任务

### 6.6.3 何时用 Skill、何时用 Sub-agent

**用 Skill**：
- 流程固定，不需要 LLM 推理
- 跑脚本、出报告
- 团队规范

**用 Sub-agent**：
- 需要**深度推理**的任务
- 需要**隔离上下文**（大量读文件）
- 任务可以**并行**（多个 sub-agent 一起干）

**用 Skill + Sub-agent**：
- Skill 提供**流程框架**
- Sub-agent 执行**推理密集**的步骤
- `context: fork` 启用 sub-agent

---

## 6.7 体系级架构模式

### 6.7.1 模式 1：基础包 + 领域包

```
基础包（基础能力）：
  - data-formatter      (格式化输出)
  - error-handler       (统一错误处理)
  - file-helper         (文件操作封装)

领域包（业务能力）：
  - finance-report      (财务报表，引用 data-formatter)
  - sales-analysis      (销售分析，引用 data-formatter)
  - hr-summary          (HR 总结，引用 data-formatter)
```

### 6.7.2 模式 2：基础 + 适配

```
基础 skill: data-validator
  - 通用数据验证规则

适配 skill 1: data-validator-finance
  - 金融领域特定验证（汇率精度、币种一致性）

适配 skill 2: data-validator-medical
  - 医疗领域特定验证（HIPAA 合规）
```

### 6.7.3 模式 3：流水线编排

```
orchestrator-skill: data-pipeline
  - 调用 analyzer-skill 分析数据
  - 调用 transformer-skill 转换格式
  - 调用 reporter-skill 生成报告
  - 调用 notifier-skill 通知用户
```

**实现**：在 orchestrator 主体里**显式**告诉 Claude 用 `/skill-name`

### 6.7.4 模式 4：插件市场

```
# 第三方 skill 仓库
my-org-skills/
├── finance/
│   ├── tax-calculator
│   ├── invoice-generator
│   └── audit-checker
├── marketing/
│   ├── seo-analyzer
│   ├── social-poster
│   └── email-composer
└── dev-tools/
    ├── docker-helper
    ├── k8s-debugger
    └── log-analyzer

# 用户只装需要的子集
ln -s my-org-skills/finance/tax-calculator ~/.claude/skills/
```

---

## 6.8 监控与可观测性

### 6.8.1 关注的核心指标

| 指标 | 含义 | 怎么测 |
|------|------|--------|
| **触发率** | skill 被触发的频率 | Claude Code 日志 |
| **触发准确率** | 触发后是否完成任务 | 用户反馈 |
| **误触发率** | 触发后无意义 | 用户反馈 |
| **加载成功率** | SKILL.md 解析成功率 | 启动日志 |
| **平均加载 token** | 加载到上下文的 token 数 | `/context` |
| **执行成功率** | 脚本执行成功比例 | 脚本日志 |
| **用户满意度** | 主观评价 | 问卷 |

### 6.8.2 调试工具

**Claude Code 内置**：

```bash
/context        # 看当前上下文占用
/help           # 列出所有 skill 和命令
/cost           # 看 token 成本
```

**Skills API**：

```python
# 看 skill 列表
client.beta.skills.list()

# 看版本历史
client.beta.skills.versions.list(skill_id)
```

### 6.8.3 错误监控

```python
# 自定义监控（应用层）
def chat_with_skill_monitored(skill_id, message):
    start = time.time()
    try:
        result = chat_with_skill(skill_id, message)
        log_metric("skill.success", 1, tags={"skill_id": skill_id})
        return result
    except Exception as e:
        log_metric("skill.error", 1, tags={
            "skill_id": skill_id,
            "error": type(e).__name__
        })
        raise
    finally:
        log_metric("skill.latency", time.time() - start)
```

### 6.8.4 定期审查

**月度审查清单**：

- [ ] 哪些 skill 从未触发？（考虑删除）
- [ ] 哪些 skill 经常误触发？（改 description）
- [ ] 哪些 skill token 占用大？（精简或拆 reference）
- [ ] 哪些 skill 执行失败率高？（修脚本或加错误处理）
- [ ] 团队成员装了哪些 skill？（统一管理）

---

## 6.9 安全设计

### 6.9.1 Skill 的攻击面

**风险**：
- Skill 包含可执行代码
- Skill 连接到外部网络
- Skill 处理敏感数据

**攻击场景**：
- 恶意 skill 注入（第三方来源不可信）
- 供应链攻击（依赖被污染）
- 数据外泄（脚本读取 ~/.ssh/id_rsa）
- 提示词注入（description 里藏恶意指令）

### 6.9.2 防御措施

**1. 来源审计**

```bash
# 安装前审查
git clone https://github.com/suspicious/skill-repo
# 检查：
#   - 是否有 scripts/ 里跑可疑命令？
#   - 是否有外部网络请求？
#   - 是否有读写 ~/.ssh、~/.aws 等敏感路径？
```

**2. 工具白名单**

```yaml
# 限制 skill 只能用必要工具
allowed-tools:
  - Read
  - Grep
  - Bash(python *)     # 限定只能跑 python
  # 不给 Write、Edit、危险 Bash
```

**3. 路径白名单**

```yaml
paths:
  - "src/**/*"
  - "tests/**/*"
  # 不给访问 .env、secrets/、node_modules/
```

**4. 用户确认**

```yaml
# 危险操作需要用户确认
disable-model-invocation: true   # 只能手动触发
```

**5. 企业管控**

```
企业级 Managed Settings：
  - 限制可装 skill 来源
  - 强制代码扫描
  - 审计所有 skill 行为
  - 异常告警
```

### 6.9.3 审计清单

- [ ] Skill 来源可信（官方 / 内部 / 知名社区）
- [ ] 已审查所有 SKILL.md 内容
- [ ] 已审查所有 scripts/ 脚本
- [ ] 没有外网请求（除非必要）
- [ ] 没有读写敏感路径
- [ ] 没有收集 / 上传用户数据
- [ ] 有 allowed-tools 限制
- [ ] 有明确版本来源

---

## 6.10 体系设计 checklist

设计 Skill 体系时按这个清单检查：

### 命名 & 作用域

- [ ] 命名体现**领域 + 功能**
- [ ] 避免与现有 skill 重名
- [ ] 明确每个 skill 的作用域（个人 / 项目 / 企业）

### 内容组织

- [ ] 每个 skill 主体 < 500 行
- [ ] description 100 词左右
- [ ] 引用结构清晰（SKILL.md → references/）
- [ ] 脚本职责单一

### 调用控制

- [ ] 危险 skill 用 `disable-model-invocation: true`
- [ ] 后台 skill 用 `user-invocable: false`
- [ ] paths 限制适用范围
- [ ] allowed-tools 限制能力

### 协同设计

- [ ] 多 skill 职责**不重叠**
- [ ] 互斥 skill 在 description 互相排除
- [ ] 串行 / 并行模式明确
- [ ] 与 MCP / Sub-agent 边界清晰

### 监控 & 安全

- [ ] 监控触发率和误触发率
- [ ] 定期审查未使用的 skill
- [ ] 来源审计机制
- [ ] 工具 / 路径白名单
- [ ] 版本管理策略

### 文档

- [ ] 每个 skill 有清晰用途说明
- [ ] 团队成员知道怎么装 / 怎么用
- [ ] 有升级 / 废弃流程

---

## 6.11 真实案例：10 人团队怎么设计

**场景**：10 人前端团队，迭代节奏 2 周/次，需要 review、test、deploy 等环节

### 设计方案

**个人级**：
```
~/.claude/skills/
├── my-personal-prefs/      # 个人偏好（输出语言、代码风格）
└── quick-snippets/         # 个人速查
```

**项目级**（git 共享）：
```
.claude/skills/
├── fe-code-review/         # 前端代码审查（Vue/React）
├── fe-test-gen/            # 单元测试生成
├── commit-msg/             # commit 信息规范
├── pr-template/            # PR 模板生成
└── i18n-helper/            # 国际化文案
```

**企业级**（Managed Settings）：
```
managed-skills/
├── company-coding-style/   # 全公司代码规范
├── security-scan/          # 安全扫描基线
└── legal-compliance/       # 合规检查
```

### 关键设计

1. **企业级强制基础规范**——谁都必须用
2. **项目级沉淀团队规范**——git 共享
3. **个人级允许个人偏好**——不冲突别人
4. **多 skill 协同**：commit-msg + pr-template 配合，fe-code-review + security-scan 配合

### 监控

- 每月 review skill 列表
- 看哪些 skill 触发率低（可能没用）
- 看哪些 skill 误触发率高（需改）
- 收集团队反馈

---

## 6.12 接下来

- 想了解不同 IDE / 平台的 skill 体系差异 → [第 7 章 · 生态对照](./07-ecosystem.md)
- 触发 / 加载有问题想排查 → [第 8 章 · 调试与反模式](./08-debug.md)
