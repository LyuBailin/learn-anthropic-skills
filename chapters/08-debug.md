# 第 8 章 · 调试与反模式：常见坑 + 排查方法

> 读完这一章你应该能：① 排查"skill 不触发 / 误触发 / 加载失败"；② 识别 12 个常见反模式；③ 用调试工具定位问题。

---

## 8.1 问题分类与排查路径

| 问题类型 | 现象 | 排查起点 |
|---------|------|---------|
| **不触发** | 用户输入匹配但 skill 不加载 | description / paths / 调用控制 |
| **误触发** | 不该触发时触发了 | description 范围 |
| **加载失败** | Claude 报错，无法读 SKILL.md | YAML 语法 / 权限 |
| **执行失败** | 加载了但脚本跑不起来 | 脚本逻辑 / 依赖 |
| **性能问题** | 加载慢 / token 撑爆 | skill 大小 / 数量 |
| **结果不对** | 触发 + 执行都成功但答案错 | skill 主体逻辑 |

---

## 8.2 "完全不触发"

### 排查清单

```bash
# 1. 确认 skill 已被发现
ls ~/.claude/skills/my-skill/SKILL.md

# 2. 确认 frontmatter 格式正确
head -20 ~/.claude/skills/my-skill/SKILL.md
# 必须有：--- 包围的 YAML，包含 name 和 description

# 3. 在 Claude Code 里查
> What skills are available?
# 或
> 列出所有可用的 skill
```

### 常见原因

**原因 1：description 关键词不匹配**

```yaml
# ❌ description 没关键词
description: A skill for handling documents.

# ✅ 加关键词
description: 整理 PDF、Word、Excel 等办公文档，包括格式转换、内容提取。
```

**解决**：在 description 里加**用户实际会说的词**

**原因 2：paths 过严**

```yaml
# ❌ paths 太严
paths:
  - "src/api/v2/endpoints.ts"
# 只有当对话涉及这个文件时才会考虑

# ✅ 放宽
paths:
  - "src/api/**/*.ts"
```

**原因 3：误设了 `disable-model-invocation`**

```yaml
# ❌ 禁止 Claude 自动触发
disable-model-invocation: true

# ✅ 如果想让 Claude 自动触发，删掉这行
```

**原因 4：YAML 解析失败**

```bash
# 检查 YAML 语法
python -c "import yaml; yaml.safe_load(open('SKILL.md').read().split('---')[1])"
```

---

## 8.3 "误触发"

**现象**：用户问 X，skill 跑出来但跟 X 无关

### 排查清单

**1. description 范围太广**

```yaml
# ❌ 太广
description: 处理文档相关任务。

# ✅ 收紧
description: |
  仅当用户**明确要求生成 PDF 文档**时使用——
  不是读 PDF、不是 Word、不是 Excel。
```

**2. 加负向触发**

```yaml
description: |
  审查 Python 代码并生成测试。
  适用：用户说"review python"、"为这段代码写测试"。
  不适用：审查其他语言（用 language-specific skill）、仅解释代码（用普通对话）。
```

**3. paths 限制**

```yaml
# 只在涉及 .py 文件时考虑
paths:
  - "**/*.py"
```

---

## 8.4 "加载失败 / 解析错误"

### 错误类型

**错误 1：YAML 语法错误**

```yaml
# ❌ 缩进错误
allowed-tools:
- Read
  - Grep

# ✅ 一致缩进
allowed-tools:
  - Read
  - Grep
```

**错误 2：缺少必填字段**

```
Error: SKILL.md missing required field 'description'
```

**解决**：确保 `name` 和 `description` 都在 frontmatter 里

**错误 3：name 命名违规**

```
Error: skill name must be lowercase with hyphens
```

**解决**：检查 name 字段

**错误 4：文件权限**

```
Error: Permission denied reading SKILL.md
```

**解决**：
```bash
chmod 644 SKILL.md
```

**错误 5：编码问题**

```
Error: failed to decode SKILL.md as UTF-8
```

**解决**：
```bash
iconv -f GBK -t UTF-8 SKILL.md > SKILL.utf8.md
mv SKILL.utf8.md SKILL.md
```

---

## 8.5 "执行失败"

**现象**：skill 加载成功，Claude 调用脚本但脚本崩了

### 排查

**1. 看错误消息**

```python
# 让脚本输出更详细错误
import traceback
try:
    do_something()
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
```

**2. 检查依赖**

```bash
# 列出依赖
python -c "import required_lib"
# 报错就装
pip install required_lib
```

**3. 检查权限**

```bash
# 脚本无执行权限
chmod +x scripts/*.py
```

**4. 检查路径**

```python
# ❌ 硬编码绝对路径
SCRIPT_PATH = "/home/user/.claude/skills/my-skill/scripts/run.py"

# ✅ 用相对路径或内置变量
SCRIPT_PATH = "${CLAUDE_SKILL_DIR}/scripts/run.py"
```

---

## 8.6 "性能问题"

**现象**：加载慢、token 撑爆、响应延迟

### 优化清单

**1. 减少 L1 元数据**

```yaml
# description 控制在 100 词以内
# 拆分大 skill 为多个小 skill
```

**2. 减少 L2 主体**

```markdown
<!-- SKILL.md 控制在 500 行以内 -->
<!-- 超过 → 拆 references/ -->
```

**3. 减少 L3 资源**

```markdown
<!-- reference 单文件 < 200 行 -->
<!-- 大量数据用脚本生成，不放 markdown -->
```

**4. 减少 skill 数量**

```bash
# 删除不用的 skill
rm -rf ~/.claude/skills/old-skill/

# 合并相似 skill
```

**5. 用 `disable-model-invocation` 排除**

```yaml
# 手动调用的 skill 不进 L1
disable-model-invocation: true
```

**6. 用脚本代替文档**

```python
# ❌ 在 SKILL.md 里写大段 SQL 规则
# ✅ 写 validate_sql.py 脚本，Claude 跑
```

---

## 8.7 12 个常见反模式

### 反模式 1：description 写得太弱

```yaml
# ❌ 反模式
description: Helper for documents.

# 问题：什么都不会触发
```

**修正**：
```yaml
description: |
  从 Markdown / JSON / CSV 生成专业 PDF。
  当用户说"创建 PDF"、"导出报告"、"生成发票"时使用。
```

### 反模式 2：description 写得太泛

```yaml
# ❌ 反模式
description: Handles all software engineering tasks.

# 问题：什么都会触发，污染上下文
```

**修正**：
```yaml
description: |
  审查 Go 语言的微服务代码。
  仅当用户提到"Go"、"微服务"或"review go code"时使用。
```

### 反模式 3：把整个工作流塞进主体

```yaml
# ❌ 反模式：主体 2000 行
---
name: my-skill
description: ...
---
[2000 行 markdown...]
```

**修正**：
```markdown
# 主体 < 500 行
## 工作流程
简述

## 详细
详见 [details.md](details.md)  <!-- 拆出去 -->
```

### 反模式 4：脚本里写对话感知逻辑

```python
# ❌ 反模式：脚本读取 stdin 期望对话内容
user_input = sys.stdin.read()
response = llm_call(user_input)  # 用 LLM 处理！
```

**修正**：
```python
# ✅ 脚本只做确定性工作
def validate(fields: dict) -> bool:
    # 纯函数式
    ...
```

### 反模式 5：硬编码敏感信息

```python
# ❌ 反模式
API_KEY = "sk-ant-1234567890"
```

**修正**：
```python
import os
API_KEY = os.environ["ANTHROPIC_API_KEY"]
```

### 反模式 6：不给 allowed-tools

```yaml
# ❌ 反模式：skill 可以用任何工具
# 危险：可能误删文件、误推代码
```

**修正**：
```yaml
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(python *)
  # 不给 Write、Edit、不限制的 Bash
```

### 反模式 7：危险操作没加 disable-model-invocation

```yaml
# ❌ 反模式
---
name: deploy
description: 部署到生产环境
---
# 任何对话都可能触发部署！
```

**修正**：
```yaml
disable-model-invocation: true
# 只能手动 /deploy
```

### 反模式 8：依赖没说清

```markdown
# ❌ SKILL.md 里说"运行 scripts/analyze.py"
# 但用户没装 pandas
```

**修正**：
```markdown
## 环境要求
首次使用前需要安装：
- Python 3.10+
- pandas
- matplotlib
运行 `pip install pandas matplotlib`
```

### 反模式 9：脚本路径硬编码

```python
# ❌ 反模式
subprocess.run(["python", "/home/alice/.claude/skills/my-skill/scripts/x.py"])
# 别人用就崩
```

**修正**：
```bash
# 用环境变量
python "${CLAUDE_SKILL_DIR}/scripts/x.py"
```

### 反模式 10：YAML 字符串里有特殊字符没转义

```yaml
# ❌ 反模式
description: Use when: PDF, forms, document.

# 问题：冒号、逗号可能引起 YAML 解析问题
```

**修正**：
```yaml
description: |
  Use when: PDF, forms, document generation.
# 或者
description: "Use when: PDF, forms, document."
```

### 反模式 11：拆得太细，几十个 skill

```
# ❌ 反模式
review-security
review-performance
review-style
review-naming
review-tests
review-docs
... 20 个 review 类 skill
```

**修正**：
```yaml
# 一个 review 类 skill，加 when_to_use
name: code-review
description: |
  综合代码审查，涵盖安全 / 性能 / 风格。
  - 用户说"review"时触发
  - 用户说"只要安全审查"时也触发
when_to_use: |
  自动覆盖四个维度。用户特别指明维度时只输出该维度。
```

### 反模式 12：与现有工具 / MCP 职责重叠

```yaml
# ❌ 反模式
# 已经有 notion MCP 读 Notion，又写一个 notion-reader skill
# 已经有 github MCP，又写一个 git-commit skill
```

**修正**：
- Skill 给**流程**
- MCP 给**工具**
- 不要让 skill 做 MCP 已经做的事

---

## 8.8 调试工具箱

### Claude Code 内置

```bash
/help                 # 列出所有 skill 和命令
/context              # 看当前上下文占用
/clear                # 清空对话
/cost                 # 看 token 消耗
/compact              # 压缩上下文
```

### Minimax Code 中

```
> 列出可用 skill
> skill X 加载了什么内容
> 为什么不用 skill X
> skill X 的 description 是什么
```

### 自检脚本

```bash
#!/bin/bash
# check-skill.sh - 自检一个 skill 目录

SKILL_DIR=$1

echo "=== Checking $SKILL_DIR ==="

# 1. SKILL.md 存在
if [ ! -f "$SKILL_DIR/SKILL.md" ]; then
    echo "❌ SKILL.md 不存在"
    exit 1
fi

# 2. YAML frontmatter 格式
if ! head -1 "$SKILL_DIR/SKILL.md" | grep -q "^---$"; then
    echo "❌ SKILL.md 不是以 --- 开头"
    exit 1
fi

# 3. 必填字段
if ! grep -q "^name:" "$SKILL_DIR/SKILL.md"; then
    echo "❌ 缺少 name 字段"
    exit 1
fi
if ! grep -q "^description:" "$SKILL_DIR/SKILL.md"; then
    echo "❌ 缺少 description 字段"
    exit 1
fi

# 4. description 长度
DESC_LEN=$(awk '/^---$/{f=!f; next} f && /^description:/{f=2} f==2' "$SKILL_DIR/SKILL.md" | wc -c)
if [ "$DESC_LEN" -gt 2000 ]; then
    echo "⚠️ description 较长（$DESC_LEN 字符），建议精简"
fi

# 5. 主体长度
BODY_LINES=$(awk '/^---$/{c++; next} c==2' "$SKILL_DIR/SKILL.md" | wc -l)
if [ "$BODY_LINES" -gt 500 ]; then
    echo "⚠️ 主体较长（$BODY_LINES 行），建议拆 reference"
fi

# 6. 脚本可执行
find "$SKILL_DIR/scripts" -name "*.py" -o -name "*.sh" | while read f; do
    if [ ! -x "$f" ]; then
        echo "⚠️ $f 不可执行"
    fi
done

echo "✓ 自检完成"
```

```bash
chmod +x check-skill.sh
./check-skill.sh ~/.claude/skills/my-skill/
```

### 手动触发测试

```bash
# 在 Claude Code 中
> /skill-name test-arg
# 看是否触发、执行、返回结果
```

### 日志

```bash
# Claude Code 默认日志位置
~/.claude/logs/        # macOS/Linux
%USERPROFILE%\.claude\logs\   # Windows

# 看 skill 加载、触发、错误
grep -i "skill" ~/.claude/logs/*.log
```

---

## 8.9 调试流程图

```
Skill 有问题
    ↓
[完全不触发] → 检查 description / paths / 调用控制
    ↓ 还不行
    ↓         → 看 Claude Code 启动日志
    ↓
[误触发] → 收紧 description，加负向触发，加 paths
    ↓
[加载失败] → 跑自检脚本，验证 YAML 语法
    ↓
[执行失败] → 手动跑脚本，看错误信息
    ↓
[性能问题] → 看 /context，删未用 skill，拆大 skill
    ↓
[结果不对] → 改 skill 主体，加 reference，给更多示例
```

---

## 8.10 性能基准与 SLA

### 经验数字

| 指标 | 优秀 | 可接受 | 需优化 |
|------|------|--------|--------|
| **description 长度** | < 100 词 | 100-200 词 | > 200 词 |
| **主体长度** | < 200 行 | 200-500 行 | > 500 行 |
| **skill 总数（个人）** | < 10 | 10-30 | > 30 |
| **L1 常驻 token** | < 5K | 5-15K | > 15K |
| **单 skill 加载时间** | < 500ms | 500-1500ms | > 1500ms |
| **触发准确率** | > 90% | 70-90% | < 70% |

### 优化 checklist

- [ ] 所有 skill 的 description 长度合理
- [ ] 所有 skill 的主体 < 500 行
- [ ] 总 skill 数 < 30（个人级）
- [ ] L1 token < 15K
- [ ] 触发准确率 > 80%
- [ ] 误触发率 < 10%
- [ ] 无加载失败
- [ ] 无脚本崩溃

---

## 8.11 复盘与迭代

### 持续改进循环

```
观察 → 调优 → 验证 → 沉淀
 ↑                        ↓
 └────────────────────────┘
```

**观察**：
- 用户反馈（"这个 skill 不准"）
- `/context` 数据（"这个 skill 加载很大"）
- 触发日志（"这个 skill 经常误触发"）

**调优**：
- 改 description
- 拆 reference
- 加 paths
- 改 allowed-tools

**验证**：
- 跑自检脚本
- 重新触发测试
- 收集用户反馈

**沉淀**：
- 把发现写进 skill 的"已知问题"段落
- 总结反模式，更新团队规范
- 给 skill 加版本号

### 团队复盘会议

**月度**（30 min）：
- 看 skill 列表变化
- 看哪些 skill 触发率高
- 收集团队反馈
- 决策：删除 / 优化 / 新增

**季度**（1 h）：
- 大版本升级
- 跨团队对齐
- 安全审计

---

## 8.12 资源

- 官方故障排查：<https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview>
- Claude Code 调试：<https://code.claude.com/docs/en/skills>
- 社区讨论：GitHub Issues、Reddit r/ClaudeAI

---

## 8.13 接下来

- 想看完整示例 → [第 4 章 · 实战编写](./04-writing.md)
- 想了解不同平台的 skill 体系 → [第 7 章 · 生态对照](./07-ecosystem.md)
- 回到项目根 → [README](../README.md)
