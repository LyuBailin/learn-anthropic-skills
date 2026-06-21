# 第 4 章 · 实战编写：4 个完整可运行示例

> 这一章给你 4 个端到端可用的 skill，覆盖不同场景和复杂度。**所有示例都放在 [`examples/`](../examples/) 目录**，可以直接复制使用。

---

## 示例目录

| 示例 | 主题 | 关键能力 | 难度 |
|------|------|---------|------|
| [4.1 · pdf-form-filler](#41-pdf-form-fillerpdf-表单填写) | PDF 表单提取与填写 | scripts + references | ⭐⭐ |
| [4.2 · code-review](#42-code-review代码审查) | git 集成代码审查 | paths + allowed-tools | ⭐⭐⭐ |
| [4.3 · meeting-minutes](#43-meeting-minutes会议纪要) | 中文会议整理 | 多 references + context: fork | ⭐⭐⭐ |
| [4.4 · api-skill-python](#44-api-skill-pythonapi-集成) | Python SDK 集成 | Files API + Code Execution | ⭐⭐⭐⭐ |

---

## 4.1 · pdf-form-filler（PDF 表单填写）

> **场景**：用户上传一个 PDF 表单文件，希望 Claude 帮他填上内容。
> **价值**：体现"scripts + references + L3 资源按需加载"的完整工作流。
> **来源**：参考 Anthropic 官方 PDF skill 案例。

### 4.1.1 目录结构

```
pdf-form-filler/
├── SKILL.md
├── scripts/
│   ├── extract_fields.py     # 提取 PDF 表单字段
│   ├── fill_pdf.py           # 填写 PDF
│   └── validate.py           # 验证填写结果
├── references/
│   ├── forms.md              # 表单填写细节
│   └── acroform.md           # AcroForm 规范
├── assets/
│   └── sample.pdf            # 示例 PDF
└── LICENSE.txt
```

### 4.1.2 SKILL.md

```yaml
---
name: pdf-form-filler
description: |
  填写 PDF 表单文件。自动提取表单字段、询问用户填入值、生成填写后的 PDF。
  当用户上传 PDF 并说"填表"、"填这个表单"、"帮我填 PDF"、"fill this form"时使用。
  支持 AcroForm 标准的 PDF（包括 W-9、发票、申请表的常见模板）。
when_to_use: |
  Use this skill when the user provides a PDF file and wants to fill
  in form fields. Do NOT use this skill for: reading PDF text content
  (use document reading), signing PDFs, or creating new PDFs from scratch.
paths:
  - "*.pdf"
allowed-tools:
  - Read
  - Bash(python *)
  - Bash(pip install *)
argument-hint: "[pdf-file-path]"
---

# PDF Form Filler

## 工作流程

### 步骤 1：检查环境

确保 `pypdf` 或 `pdfrw` 库已安装：

```bash
python -c "import pypdf; print(pypdf.__version__)" 2>/dev/null || pip install pypdf
```

### 步骤 2：提取表单字段

运行 extract_fields.py，列出 PDF 的所有表单字段：

```bash
python scripts/extract_fields.py <pdf-path>
```

输出示例：
```json
{
  "fields": [
    {"name": "first_name", "type": "text", "required": true},
    {"name": "last_name", "type": "text", "required": true},
    {"name": "address", "type": "text", "required": false},
    {"name": "signature", "type": "text", "required": true}
  ]
}
```

### 步骤 3：询问用户

对每个 `required: true` 的字段，**必须**询问用户填什么。
对 `required: false` 的字段，可以跳过但提示用户。

**关键**：**永远不要自动猜测用户身份信息**（姓名、地址、SSN）。
如果用户没提供 → 询问。

### 步骤 4：填写 PDF

```bash
python scripts/fill_pdf.py <pdf-path> <output-path> \
  --field first_name="张" \
  --field last_name="三" \
  --field address="北京市朝阳区"
```

### 步骤 5：验证

```bash
python scripts/validate.py <output-path>
```

打开 PDF 检查所有必填字段都已填上。

## 关键决策点

- **必填字段用户没回答** → 不要用空值填充，提示用户必须提供
- **PDF 没有表单字段** → 提示用户这是普通 PDF，不是表单
- **PDF 加密** → 先解密（需要密码）
- **字段类型不在支持列表** → 跳过并在结果中标注

## 错误处理

| 错误 | 处理 |
|------|------|
| ModuleNotFoundError | 提示安装 `pip install pypdf` |
| FileNotFoundError | 检查文件路径 |
| PDF 加密 | 提示用户提供密码 |
| 字段不存在 | 输出哪些字段不存在 |

## 相关资源

- 表单填写详细说明见 [references/forms.md](references/forms.md)
- AcroForm 规范见 [references/acroform.md](references/acroform.md)
```

### 4.1.3 scripts/extract_fields.py

```python
#!/usr/bin/env python3
"""提取 PDF 表单的所有字段信息"""

import sys
import json
from pathlib import Path

def extract_fields(pdf_path: str) -> dict:
    try:
        from pypdf import PdfReader
    except ImportError:
        print(json.dumps({
            "error": "pypdf not installed",
            "fix": "pip install pypdf"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    if not Path(pdf_path).exists():
        print(json.dumps({
            "error": f"File not found: {pdf_path}"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    reader = PdfReader(pdf_path)

    if reader.is_encrypted:
        print(json.dumps({
            "error": "PDF is encrypted",
            "fix": "Decrypt first or provide password"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    fields = reader.get_fields() or {}

    result = {
        "file": pdf_path,
        "page_count": len(reader.pages),
        "field_count": len(fields),
        "fields": [
            {
                "name": name,
                "type": str(info.get("/FT", "unknown")).replace("/", ""),
                "required": info.get("/Ff", 0) & 2 == 2,  # /Ff bit 1 = required
                "value": info.get("/V", ""),
                "options": info.get("/Opt", None)  # for choice fields
            }
            for name, info in fields.items()
        ]
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: extract_fields.py <pdf-path>")
        sys.exit(1)
    extract_fields(sys.argv[1])
```

### 4.1.4 scripts/fill_pdf.py

```python
#!/usr/bin/env python3
"""填写 PDF 表单"""

import sys
import json
import argparse
from pathlib import Path

def parse_field_args(args):
    """解析 --field name=value 参数"""
    fields = {}
    for arg in args:
        if "=" not in arg:
            continue
        name, value = arg.split("=", 1)
        fields[name] = value
    return fields

def fill_pdf(input_path: str, output_path: str, fields: dict):
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print(json.dumps({"error": "pypdf not installed"}))
        sys.exit(1)

    reader = PdfReader(input_path)
    writer = PdfWriter()

    # 复制所有页面
    for page in reader.pages:
        writer.add_page(page)

    # 填写字段
    writer.update_page_form_field_values(
        writer.pages[0],
        fields
    )

    # 处理只读字段（"signature" 等）
    # pypdf 默认保留只读字段的现有值

    with open(output_path, "wb") as f:
        writer.write(f)

    print(json.dumps({
        "status": "ok",
        "input": input_path,
        "output": output_path,
        "fields_filled": len(fields),
        "field_names": list(fields.keys())
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--field", action="append", default=[])
    args = parser.parse_args()

    fields = parse_field_args(args.field)
    fill_pdf(args.input, args.output, fields)
```

### 4.1.5 references/forms.md

```markdown
# PDF 表单填写详细说明

## 字段类型

| AcroForm 类型 | 处理方式 |
|--------------|---------|
| /Tx (Text) | 直接填字符串 |
| /Btn (Button) | 单选/复选/按钮，需要特殊处理 |
| /Ch (Choice) | 下拉/列表，从预定义值选 |
| /Sig (Signature) | 通常不程序化填写，提示用户手动签 |

## 必填字段判断

PDF 规范用 `/Ff` 标志位（Field Flags）：
- bit 1 (`0x02`) = Required
- bit 2 (`0x04`) = NoExport
- bit 3 (`0x08`) = NoToggleToOff
- bit 13 (`0x1000`) = Multiline
- bit 14 (`0x2000`) = Password
- bit 15 (`0x4000`) = NoToggleToOn
- bit 16 (`0x8000`) = RadiosInUnison
- bit 17 (`0x10000`) = CommitOnSelChange
- bit 25 (`0x1000000`) = FileSelect

## 常见问题

### Q: 填写后字段值不显示？
A: 多数 PDF 需要先 `update_page_form_field_values` 再重新生成。

### Q: "signature" 字段无法填写？
A: 数字签名是图像，程序无法直接添加。

### Q: 字段名带特殊字符？
A: 用 JSON 配置文件传字段，避免命令行参数解析问题。

## 进阶用法

- **批量填写**：用 JSON 文件传字段
- **模板化**：保存常用填写模板
- **验证规则**：添加字段值校验（邮箱格式、电话格式）
```

### 4.1.6 测试

```bash
# 准备一个简单的 PDF 表单（可以用 Adobe Acrobat 创建）
# 假设表单有 first_name, last_name, email 三个字段

# 1. 提取字段
python ~/.claude/skills/pdf-form-filler/scripts/extract_fields.py sample.pdf

# 2. 在 Claude Code 中：
#    "用 pdf-form-filler 帮我填 sample.pdf，first_name=张, last_name=三, email=zhang@example.com"
```

---

## 4.2 · code-review（代码审查）

> **场景**：用户改完代码想让 Claude 审查。
> **价值**：体现 paths 过滤、allowed-tools 白名单、git 集成。

### 4.2.1 目录结构

```
code-review/
├── SKILL.md
├── references/
│   ├── security-checklist.md    # 安全审查清单
│   └── style-guide.md           # 团队代码风格
└── examples/
    └── good-pr.md               # 一个标准 PR 的范例
```

### 4.2.2 SKILL.md

```yaml
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

## 工作流程

### Step 1：收集变更

```bash
git status                    # 看修改了哪些文件
git diff HEAD                 # 工作区 + staged 完整 diff
git diff --stat HEAD          # 变更统计
```

如果用户指定 base branch（如 `main`），用：
```bash
git diff main...HEAD          # 对比 main 与当前
```

### Step 2：分类审查

按严重度从高到低：

#### 🔴 P0：安全问题（必须修复）

- 硬编码的 secret（API key、密码、token、private key）
- SQL 注入风险（字符串拼接 SQL）
- 命令注入（`os.system(user_input)`）
- 路径遍历（`open(user_path)` 没校验）
- XSS（`innerHTML` 拼接未转义）
- 不安全的反序列化（`pickle.loads` 不可信数据）
- SSRF（用户控制的 URL 没校验）

#### 🟡 P1：建议改进

- 错误处理（catch 块为空、错误消息泄露内部细节）
- 资源泄漏（文件未关闭、连接未释放）
- 命名不清（a, tmp, data, x）
- 函数过长（> 50 行）
- 嵌套过深（> 3 层）
- 重复代码
- 性能问题（N+1 查询、不必要的同步循环）

#### 🟢 P2：亮点

- 测试覆盖了边界
- 错误处理完善
- 命名清晰有业务含义
- 注释解释"为什么"而非"做什么"
- 复用了已有工具

### Step 3：输出

按以下格式输出：

```markdown
## Code Review — <branch-name>

### 变更统计
- 文件数：N
- 新增：+N 行
- 删除：-N 行

### 🔴 严重问题
1. **[问题简述]** — `file:line`
   - 问题：详细描述
   - 建议：如何修复

### 🟡 建议改进
1. **[建议简述]** — `file:line`
   - 现状：...
   - 建议：...

### 🟢 亮点
- xxx

### 📋 总结
- 建议：可以合并 / 需修改 / 需重大修改
- 关键关注：xxx
```

## 关键决策点

- **变更太大**（> 500 行）→ 建议拆成多个 commit / PR
- **缺测试** → 标注但不强制
- **涉及第三方库源码** → 不审查
- **用户明确说"随便看看"** → 跳过 P0 检查

## 相关资源

- 安全审查详细清单见 [references/security-checklist.md](references/security-checklist.md)
- 团队代码风格见 [references/style-guide.md](references/style-guide.md)
- 标准 PR 范例见 [examples/good-pr.md](examples/good-pr.md)
```

### 4.2.3 references/security-checklist.md

```markdown
# 安全审查详细清单

## 1. 注入类漏洞

### SQL 注入
```python
# ❌ 危险
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ 安全
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

### 命令注入
```python
# ❌ 危险
os.system(f"convert {user_input} output.png")

# ✅ 安全
subprocess.run(["convert", user_input, "output.png"], check=True)
```

### 路径遍历
```python
# ❌ 危险
filename = request.GET["file"]
return open(f"/uploads/{filename}").read()

# ✅ 安全
filename = secure_filename(request.GET["file"])
full_path = os.path.join("/uploads", filename)
full_path = os.path.realpath(full_path)
if not full_path.startswith("/uploads"):
    abort(403)
```

## 2. 敏感数据

```python
# ❌ 危险
API_KEY = "sk-1234567890abcdef"

# ✅ 安全
API_KEY = os.environ["API_KEY"]
```

## 3. 加密 & 认证

- 密码必须 bcrypt / argon2 哈希
- Token 不能放 URL（应在 Authorization header）
- 不用自创加密算法
- HTTPS 强制

## 4. 错误处理

```python
# ❌ 错误：吞掉异常
try:
    do_something()
except:
    pass

# ❌ 错误：泄露内部细节
except Exception as e:
    return f"Error: {traceback.format_exc()}", 500

# ✅ 正确
except SpecificException as e:
    logger.exception("operation failed")
    return "Internal error", 500
```

## 5. 反序列化

```python
# ❌ 危险：pickle 反序列化不可信数据
data = pickle.loads(request.data)

# ✅ 安全：用 JSON
data = json.loads(request.data)
```

## 6. XSS

```javascript
// ❌ 危险
element.innerHTML = userInput;

// ✅ 安全
element.textContent = userInput;
// 或者用框架自带的转义
```

## 7. SSRF

```python
# ❌ 危险
url = request.json["url"]
return requests.get(url).text

# ✅ 安全
from urllib.parse import urlparse
url = request.json["url"]
parsed = urlparse(url)
if parsed.hostname in ALLOWED_HOSTS:
    return requests.get(url).text
```

## 自检清单

- [ ] 没有硬编码 secret
- [ ] 没有 SQL 字符串拼接
- [ ] 没有 os.system(user_input)
- [ ] 文件路径已校验
- [ ] 密码用 bcrypt
- [ ] 异常不泄露内部细节
- [ ] 没有 pickle 反序列化
- [ ] 没有 innerHTML 拼接
- [ ] SSRF 域名已白名单
```

### 4.2.4 测试

```bash
# 在 Claude Code 中
# 1. 修改一些代码
# 2. 触发 skill
> /code-review
# 或者
> 帮我 review 一下当前的改动
```

---

## 4.3 · meeting-minutes（会议纪要）

> **场景**：用户给一段会议录音转写文本，希望整理成结构化纪要。
> **价值**：体现**多 reference 按需加载**（不同会议类型用不同模板）+ **中文场景** + `context: fork`。

### 4.3.1 目录结构

```
meeting-minutes/
├── SKILL.md
└── references/
    ├── weekly.md            # 周会模板
    ├── retrospective.md     # 复盘会模板
    ├── client.md            # 客户沟通模板
    └── all-hands.md         # 全员会模板
```

### 4.3.2 SKILL.md

```yaml
---
name: meeting-minutes
description: |
  把会议录音/转写文本整理成结构化会议纪要。支持周会、项目复盘、客户沟通、全员会四种类型，
  自动识别会议类型并应用对应模板。当用户说"整理会议"、"会议纪要"、"整理录音"时使用。
when_to_use: |
  Use this skill when the user provides meeting transcript or notes and
  wants structured minutes. Do NOT use for: general text summarization,
  or generating meeting agendas.
paths: []   # 不限定文件
context: fork
agent: general-purpose
argument-hint: "<meeting-type> <transcript-or-file>"
---

# 会议纪要 Skill

## 工作流程

### Step 1：识别会议类型

读用户提供的转写文本，根据关键词判断：

| 关键词 / 模式 | 会议类型 |
|--------------|---------|
| "上周"、"本周"、"下周"、"周会"、"weekly" | weekly |
| "做得好的"、"做得不好的"、"retro"、"复盘"、"总结" | retrospective |
| "客户"、"contract"、"合作"、"采购"、"需求" | client |
| "全员"、"all hands"、"公司"、"组织" | all-hands |

如果用户明确指定了 `<meeting-type>`，用指定的。否则用关键词推断，仍不确定时**询问用户**。

### Step 2：加载对应模板

根据类型，**只**读取对应的 reference 文件（节省 token）：

- weekly → [references/weekly.md](references/weekly.md)
- retrospective → [references/retrospective.md](references/retrospective.md)
- client → [references/client.md](references/client.md)
- all-hands → [references/all-hands.md](references/all-hands.md)

### Step 3：提取关键信息

按模板的字段，从转写文本里抽取：

- **参会人**（识别每段话的发言人）
- **议题**（按主题分段）
- **决议**（"决定…"、"确认…"、"agree"）
- **行动项**（"X 负责"、"deadline"、"截止"、"by Friday"）
- **风险 / 阻塞**（"卡在"、"问题"、"无法"、"blocker"）
- **未决议**（"下次讨论"、"待定"、"TBD"）

### Step 4：输出

按 reference 模板的格式输出。

### Step 5：保存（可选）

询问用户是否要保存到文件。如果要：
- 默认保存路径：`./minutes/YYYY-MM-DD-<meeting-type>.md`
- 文件名格式：`<日期>-<类型>-<可选主题>.md`

## 关键决策点

- **文本很短**（< 200 字） → 标注"信息不完整"，列出已知信息 + 缺失项
- **文本超长**（> 5000 字） → 用 `context: fork` 隔离处理
- **多个会议混在一段文本** → 让用户拆分，或按时间分章节
- **没有发言人标识** → 标注"未识别发言人"，但仍尝试按主题分段

## 错误处理

| 情况 | 处理 |
|------|------|
| 文本是空 | 提示用户提供内容 |
| 文本不是会议（明显是别的） | 退出并提示这不是会议转写 |
| 关键词不明确 | 列出 4 种类型让用户选 |

## 隐私

- **不要**把会议内容传到外部服务
- **不要**记录敏感信息（薪资、个人评价）到结构化字段
- 如有敏感信息，标注 `[已脱敏]`
```

### 4.3.3 references/weekly.md

```markdown
# 周会模板

## 标题
`周会 - YYYY-MM-DD`

## 参会人
- 姓名 1
- 姓名 2
- ...

## 上周进展（按人 / 按模块）

### 姓名 1
- ✅ 完成项 1
- ✅ 完成项 2
- 🚧 进行中：xxx

### 姓名 2
- ...

## 本周计划

### 姓名 1
- 计划 1
- 计划 2

## 阻塞 / 风险

- 阻塞项（谁卡在什么上）
- 需要的支持

## 决议

- 决议 1
- 决议 2

## 行动项

| 行动 | 负责人 | 截止日期 |
|------|--------|---------|
| xxx | 张三 | 2026-06-20 |
```

### 4.3.4 references/retrospective.md

```markdown
# 复盘会模板

## 标题
`复盘 - <项目名> - YYYY-MM-DD`

## 项目概述
一段话说明项目背景和目标。

## 做得好的（Keep / 继续做）

- xxx
- xxx

## 做得不好的（Drop / 不再做）

- xxx
- xxx

## 改进项（Try / 下次尝试）

| 改进项 | 负责人 | 验证方式 |
|--------|--------|---------|
| xxx | xxx | 怎么做算成功 |

## 关键数据

- 周期：N 天
- 投入：N 人日
- 主要里程碑：xxx

## 下一步

- 下一阶段：xxx
- 启动日期：xxx
```

### 4.3.5 references/client.md

```markdown
# 客户沟通模板

## 标题
`<客户名>沟通 - YYYY-MM-DD`

## 参会人

### 我方
- 姓名 1（角色）
- 姓名 2（角色）

### 客户方
- 姓名 1（职位）

## 客户诉求 / 问题

- 问题 1
- 问题 2

## 我们给出的方案 / 回应

- 方案 1
- 方案 2

## 客户反馈

- 接受 / 拒绝 / 待定
- 进一步问题

## 行动项

| 行动 | 负责人 | 截止日期 |
|------|--------|---------|
| xxx | 我方-张三 | 2026-06-20 |
| xxx | 客户-李四 | 2026-06-25 |

## 商务要点

- 价格：xxx
- 时间线：xxx
- 关键条款：xxx

## 风险

- 风险 1（应对：xxx）

## 下次沟通

- 时间：
- 议程：
```

### 4.3.6 references/all-hands.md

```markdown
# 全员会模板

## 标题
`全员会 - YYYY-MM-DD`

## 议程

1. 开场（CEO）
2. 业务进展
3. 重点项目
4. 人事变动
5. Q&A

## 业务进展

- 关键指标：xxx
- 重点成果：xxx
- 主要挑战：xxx

## 重点项目

### 项目 1
- 状态：在轨 / 风险 / 阻塞
- 下一步：xxx

## 人事变动

- 新加入：xxx
- 晋升：xxx
- 离职：xxx

## Q&A（重点）

- Q：xxx — A：xxx
- Q：xxx — A：xxx
```

### 4.3.7 测试

```bash
# 在 Claude Code 中触发
> /meeting-minutes weekly
> 把这段会议录音整理成纪要：
> [粘贴转写文本]
```

---

## 4.4 · api-skill-python（API 集成）

> **场景**：通过 Anthropic Python SDK 把 skill 集成到自己的应用里。
> **价值**：体现完整的 Messages API + Files API + Code Execution 流程。

### 4.4.1 完整的 Python 集成代码

```python
"""
api_skill_demo.py
演示如何用 Anthropic Python SDK 集成自定义 Skill
需要：anthropic >= 0.40.0
"""

import os
import json
from pathlib import Path
from anthropic import Anthropic

# ============ 配置 ============
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ============ Step 1：上传 Skill ============
# 注意：skill 必须打包成 zip 格式上传
def upload_skill(skill_dir: str, skill_name: str) -> str:
    """上传一个 skill 目录，返回 skill_id"""
    import zipfile
    import tempfile

    skill_path = Path(skill_dir)
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill directory not found: {skill_dir}")

    # 打包成 zip
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        zip_path = tmp.name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in skill_path.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(skill_path)
                zf.write(file, arcname)

    # 上传
    with open(zip_path, "rb") as f:
        skill = client.beta.skills.create(
            name=skill_name,
            skill_data=f,
            betas=["skills-2025-01-01"]
        )

    print(f"✓ Skill uploaded: {skill.id}")
    print(f"  Name: {skill.name}")
    print(f"  Version: {skill.version}")

    os.unlink(zip_path)
    return skill.id


# ============ Step 2：调用带 Skill 的对话 ============
def chat_with_skill(
    skill_id: str,
    user_message: str,
    upload_files: list[str] = None
) -> str:
    """
    用指定 skill 进行对话
    upload_files: 需要一并上传到沙箱的文件列表
    """
    # 1. 上传输入文件
    file_ids = []
    if upload_files:
        for file_path in upload_files:
            with open(file_path, "rb") as f:
                file_obj = client.beta.files.upload(
                    file=f,
                    betas=["files-api-2025-04-14"]
                )
                file_ids.append(file_obj.id)
                print(f"✓ File uploaded: {file_obj.id} ({file_path})")

    # 2. 构造消息
    message_content = []
    for fid in file_ids:
        message_content.append({
            "type": "file",
            "file": {"file_id": fid}
        })
    message_content.append({
        "type": "text",
        "text": user_message
    })

    # 3. 调用 Messages API
    response = client.beta.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        betas=["code-execution-2025-01-01", "skills-2025-01-01", "files-api-2025-04-14"],
        skills=[
            {
                "type": "custom",
                "skill_id": skill_id,
                "version": "latest"
            }
        ],
        tools=[
            {"type": "code_execution_20250101", "name": "code_execution"}
        ],
        messages=[
            {
                "role": "user",
                "content": message_content
            }
        ]
    )

    # 4. 提取文本响应
    text_parts = []
    for block in response.content:
        if hasattr(block, "text"):
            text_parts.append(block.text)
        elif block.type == "bash_code_execution_tool_result":
            # 提取沙箱中生成的文件
            if hasattr(block, "content") and hasattr(block.content, "content"):
                for result_block in block.content.content:
                    if hasattr(result_block, "file_id"):
                        text_parts.append(f"[Generated file: {result_block.file_id}]")

    return "\n".join(text_parts)


# ============ Step 3：下载沙箱输出文件 ============
def download_file(file_id: str, output_path: str):
    """从沙箱下载生成的文件"""
    file_content = client.beta.files.download(
        file_id=file_id,
        betas=["files-api-2025-04-14"]
    )
    with open(output_path, "wb") as f:
        file_content.write_to_file(f.name)
    print(f"✓ Downloaded: {output_path}")


# ============ 演示 ============
if __name__ == "__main__":
    # 1. 上传 PDF 填表 skill
    skill_id = upload_skill(
        skill_dir="./pdf-form-filler",
        skill_name="PDF Form Filler"
    )

    # 2. 用 skill 处理 PDF
    response = chat_with_skill(
        skill_id=skill_id,
        user_message="请帮我填这个 PDF 表单，first_name=张, last_name=三, email=zhang@example.com",
        upload_files=["./sample-form.pdf"]
    )

    print("\n" + "=" * 60)
    print("Claude's Response:")
    print("=" * 60)
    print(response)
```

### 4.4.2 流式响应版本

```python
def chat_with_skill_streaming(skill_id: str, user_message: str):
    """流式响应版本"""
    with client.beta.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        betas=["code-execution-2025-01-01", "skills-2025-01-01"],
        skills=[{"type": "custom", "skill_id": skill_id, "version": "latest"}],
        tools=[{"type": "code_execution_20250101", "name": "code_execution"}],
        messages=[{"role": "user", "content": user_message}]
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        print()
```

### 4.4.3 列出与管理 Skill

```python
def list_my_skills():
    """列出我创建的所有 skill"""
    skills = client.beta.skills.list(betas=["skills-2025-01-01"])
    for skill in skills.data:
        print(f"- {skill.name} ({skill.id}) - version {skill.version}")

def get_skill_versions(skill_id: str):
    """查看 skill 的版本历史"""
    versions = client.beta.skills.versions.list(
        skill_id=skill_id,
        betas=["skills-2025-01-01"]
    )
    for v in versions.data:
        print(f"- {v.version} (created: {v.created_at})")

def delete_skill(skill_id: str):
    """删除一个 skill"""
    client.beta.skills.delete(
        skill_id=skill_id,
        betas=["skills-2025-01-01"]
    )
    print(f"✓ Skill deleted: {skill_id}")
```

### 4.4.4 错误处理

```python
from anthropic import APIError, APIConnectionError, RateLimitError

def safe_chat_with_skill(skill_id: str, user_message: str, max_retries: int = 3):
    """带错误处理和重试的版本"""
    for attempt in range(max_retries):
        try:
            return chat_with_skill(skill_id, user_message)
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"⏳ Rate limited, waiting {wait}s...")
                import time
                time.sleep(wait)
            else:
                raise
        except APIConnectionError as e:
            print(f"⚠️ Connection error: {e}")
            raise
        except APIError as e:
            print(f"⚠️ API error: {e.status_code} - {e.message}")
            raise
```

### 4.4.5 环境配置

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...

# 安装
pip install anthropic python-dotenv
```

### 4.4.6 完整运行

```bash
# 1. 准备 skill 目录
cp -r examples/pdf-form-filler ./

# 2. 准备测试 PDF
# （用一个简单的 PDF 表单）

# 3. 运行
python api_skill_demo.py
```

---

## 4.5 四个示例对比

| 维度 | pdf-form-filler | code-review | meeting-minutes | api-skill-python |
|------|----------------|-------------|-----------------|------------------|
| 主题 | PDF 处理 | 代码审查 | 中文会议 | API 集成 |
| 难度 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| L1 触发方式 | 关键词 + paths 过滤 | paths 过滤 | 关键词 | 程序化 |
| L2 复杂度 | 中等 | 高 | 中等 | 中等 |
| L3 资源 | scripts + references | references | 多 references | 外部 API |
| 关键技巧 | scripts 抽逻辑 | paths + allowed-tools | 多 reference 按需 | Files API + 流式 |
| 用户场景 | 偶尔用 | 经常用 | 经常用 | 开发者集成 |

---

## 4.6 接下来

- 想看怎么从 Claude Code 调到 API → [第 5 章 · API 集成](./05-api.md)
- 想搞懂怎么设计 Skill 体系 → [第 6 章 · 体系设计](./06-design.md)
- 触发不准想排查 → [第 8 章 · 调试与反模式](./08-debug.md)
