# 第 5 章 · API 集成：Messages API + Files API + Code Execution

> 读完这一章你应该能：① 知道 Claude API 里 Skill 怎么"能干活"；② 掌握 Files API 上传下载；③ 写一个 Python/TypeScript 集成示例。

---

## 5.1 API 集成的前提条件

在 Claude API 里使用 Skill，跟 Claude Code / Claude.ai 比有**额外要求**：

| 环境 | Skill 触发 | 执行能力 | 文件系统 |
|------|----------|---------|---------|
| **Claude.ai** | ✅ 自动 | ✅ 内置 | ❌ 沙箱 |
| **Claude Code** | ✅ 自动 | ✅ Bash | ✅ 本地 |
| **Anthropic API** | ✅ 自动 | ⚠️ 需 Code Execution Tool beta | ⚠️ 需 Files API |

**关键认知**：
- **API 默认没有执行能力**——Claude 读不了文件、跑不了脚本
- **要让 Skill "能干活"，必须显式接入 Code Execution Tool**
- **要让 Claude 读用户上传的文件，必须用 Files API**

```
┌─────────────────────────────────────┐
│  Claude API 集成 Skill 的三大组件     │
├─────────────────────────────────────┤
│ 1. Skills API    加载 skill 定义     │
│ 2. Files API     上传输入/下载输出   │
│ 3. Code Execution 沙箱执行脚本       │
└─────────────────────────────────────┘
```

---

## 5.2 三个 API 详解

### 5.2.1 Skills API

**端点**：`/v1/skills`（beta）

**当前可用操作**：
- `client.beta.skills.create()` — 上传新 skill
- `client.beta.skills.list()` — 列出 skill
- `client.beta.skills.retrieve()` — 获取 skill 详情
- `client.beta.skills.delete()` — 删除 skill
- `client.beta.skills.versions.list()` — 查看版本历史

**Upload 格式**：必须先打包成 zip

```python
# Python SDK
import zipfile
from pathlib import Path

def pack_skill(skill_dir: str, output_zip: str):
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in Path(skill_dir).rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(skill_dir))

# 调用
with open("skill.zip", "rb") as f:
    skill = client.beta.skills.create(
        name="my-skill",
        skill_data=f,
        betas=["skills-2025-01-01"]
    )
```

**调用 skill**：

```python
response = client.beta.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    betas=["skills-2025-01-01"],
    skills=[
        {
            "type": "custom",          # 或 "anthropic" 用官方内置
            "skill_id": "skill_xxx",
            "version": "latest"
        }
    ],
    messages=[
        {"role": "user", "content": "用我的 skill 处理这个 PDF"}
    ]
)
```

**Beta 头**：必须包含 `skills-2025-01-01`

### 5.2.2 Files API

**为什么需要**：API 不能直接访问你的真实机器文件系统，Files API 是文件传输的桥梁。

**端点**：`/v1/files`（beta）

**Beta 头**：`files-api-2025-04-14`

**上传**：

```python
with open("./input.pdf", "rb") as f:
    file_obj = client.beta.files.upload(
        file=f,
        betas=["files-api-2025-04-14"]
    )
file_id = file_obj.id  # 后续用这个 ID 引用
```

**下载**：

```python
file_content = client.beta.files.download(
    file_id="file_xxx",
    betas=["files-api-2025-04-14"]
)
with open("./output.pdf", "wb") as f:
    file_content.write_to_file(f.name)
```

**在消息中引用**：

```python
response = client.beta.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    betas=["files-api-2025-04-14", "skills-2025-01-01"],
    skills=[{"type": "custom", "skill_id": "skill_xxx", "version": "latest"}],
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "file",
                "file": {"file_id": file_id}
            },
            {
                "type": "text",
                "text": "帮我填这个 PDF 表单"
            }
        ]
    }]
)
```

**注意事项**：
- File ID 是临时的，会话结束可能失效
- **及时下载**生成的输出
- 单个文件有大小限制（具体看官方文档）

### 5.2.3 Code Execution Tool

**为什么需要**：Skill 里如果有"需要执行脚本"的步骤，**必须**配 Code Execution Tool，否则 Claude 只能"知道流程"但**跑不起来**。

**Beta 头**：`code-execution-2025-01-01`

**启用方式**：

```python
response = client.beta.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    betas=["code-execution-2025-01-01", "skills-2025-01-01"],
    skills=[{"type": "custom", "skill_id": "skill_xxx", "version": "latest"}],
    tools=[
        {"type": "code_execution_20250101", "name": "code_execution"}
    ],
    messages=[...]
)
```

**沙箱能力**：
- ✅ 跑 bash / shell
- ✅ 创建 / 编辑 / 查看文件
- ✅ 运行 Python 脚本
- ⚠️ CPU / 内存 / 磁盘受限
- ⚠️ 通常**无互联网**（安全考虑）

**沙箱中的文件**：

如果 Skill 在沙箱中创建了文件，响应里会带 `file_id`：

```python
for block in response.content:
    if block.type == "bash_code_execution_tool_result":
        if hasattr(block, "content") and hasattr(block.content, "content"):
            for result_block in block.content.content:
                if hasattr(result_block, "file_id"):
                    generated_file_id = result_block.file_id
                    # 用 Files API 下载
```

---

## 5.3 完整的端到端示例

下面是一个**生产可用**的 Python 集成代码（已写好放在 `examples/api-skill-python/api_skill_demo.py`）：

```python
import os
import zipfile
import tempfile
from pathlib import Path
from anthropic import Anthropic

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

BETAS = [
    "code-execution-2025-01-01",
    "skills-2025-01-01",
    "files-api-2025-04-14",
]

# 1. 打包并上传 Skill
def upload_skill(skill_dir: str, name: str) -> str:
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        zip_path = tmp.name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in Path(skill_dir).rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(skill_dir))
    with open(zip_path, "rb") as f:
        skill = client.beta.skills.create(name=name, skill_data=f, betas=BETAS)
    os.unlink(zip_path)
    return skill.id

# 2. 端到端：上传文件 + 调用 skill + 下载结果
def process_pdf(skill_id: str, pdf_path: str, fields: dict):
    # 上传输入
    with open(pdf_path, "rb") as f:
        file_obj = client.beta.files.upload(file=f, betas=BETAS)

    # 调用
    response = client.beta.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        betas=BETAS,
        skills=[{"type": "custom", "skill_id": skill_id, "version": "latest"}],
        tools=[{"type": "code_execution_20250101", "name": "code_execution"}],
        messages=[{
            "role": "user",
            "content": [
                {"type": "file", "file": {"file_id": file_obj.id}},
                {"type": "text", "text": f"填写表单，字段：{fields}"}
            ]
        }]
    )

    # 提取响应
    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text += block.text

    return text

# 3. 运行
skill_id = upload_skill("./pdf-form-filler", "PDF Filler")
result = process_pdf(skill_id, "./sample.pdf", {"name": "张三"})
print(result)
```

完整可运行版本见 [`examples/api-skill-python/`](../examples/api-skill-python/)。

---

## 5.4 TypeScript / Node.js 版本

### 安装

```bash
npm install @anthropic-ai/sdk
```

### 完整示例

```typescript
import Anthropic from "@anthropic-ai/sdk";
import * as fs from "fs";
import * as path from "path";
import * as archiver from "archiver";

const client = new Anthropic();

const BETAS = [
  "code-execution-2025-01-01",
  "skills-2025-01-01",
  "files-api-2025-04-14",
];

async function uploadSkill(skillDir: string, name: string): Promise<string> {
  // 打包
  const zipPath = `${name}.zip`;
  await new Promise<void>((resolve, reject) => {
    const output = fs.createWriteStream(zipPath);
    const archive = archiver("zip", { zlib: { level: 9 } });
    output.on("close", () => resolve());
    archive.on("error", (err) => reject(err));
    archive.pipe(output);
    archive.directory(skillDir, false);
    archive.finalize();
  });

  // 上传
  const fileData = fs.readFileSync(zipPath);
  const skill = await client.beta.skills.create({
    name,
    skill_data: fileData as any,
    betas: BETAS,
  });

  fs.unlinkSync(zipPath);
  return skill.id;
}

async function processPdf(
  skillId: string,
  pdfPath: string,
  fields: Record<string, string>
) {
  // 上传输入
  const fileBuffer = fs.readFileSync(pdfPath);
  const fileObj = await client.beta.files.upload({
    file: fileBuffer as any,
    betas: BETAS,
  });

  // 调用
  const response = await client.beta.messages.create({
    model: "claude-sonnet-4-5",
    max_tokens: 4096,
    betas: BETAS,
    skills: [{ type: "custom", skill_id: skillId, version: "latest" }],
    tools: [{ type: "code_execution_20250101", name: "code_execution" }],
    messages: [
      {
        role: "user",
        content: [
          { type: "file", file: { file_id: fileObj.id } },
          { type: "text", text: `填写表单，字段：${JSON.stringify(fields)}` },
        ],
      },
    ],
  });

  // 提取响应
  let text = "";
  for (const block of response.content) {
    if ("text" in block) {
      text += block.text;
    }
  }
  return text;
}

// 运行
(async () => {
  const skillId = await uploadSkill("./pdf-form-filler", "PDF Filler");
  const result = await processPdf(skillId, "./sample.pdf", {
    name: "张三",
  });
  console.log(result);
})();
```

---

## 5.5 流式响应

处理长任务时用流式（减少等待时间、显示进度）：

```python
def stream_chat(skill_id: str, user_message: str):
    with client.beta.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        betas=BETAS,
        skills=[{"type": "custom", "skill_id": skill_id, "version": "latest"}],
        tools=[{"type": "code_execution_20250101", "name": "code_execution"}],
        messages=[{"role": "user", "content": user_message}]
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        print()
```

**事件类型**（stream 的事件）：

| 事件 | 含义 |
|------|------|
| `message_start` | 消息开始 |
| `content_block_start` | 内容块开始（文本 / 工具调用） |
| `text` | 增量文本 |
| `input_json` | 工具调用的增量参数 |
| `content_block_stop` | 内容块结束 |
| `message_delta` | 消息级元数据更新 |
| `message_stop` | 消息结束 |

TypeScript 流式：

```typescript
const stream = client.beta.messages.stream({
  // ... 参数同上
});

stream.on("text", (text) => process.stdout.write(text));
stream.on("error", (err) => console.error(err));
stream.on("end", () => console.log("\n[done]"));

await stream.done();
```

---

## 5.6 错误处理与重试

```python
import time
from anthropic import APIError, APIConnectionError, RateLimitError

def safe_chat(skill_id: str, message: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return chat_with_skill(skill_id, message)
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # 指数退避
                print(f"⏳ Rate limited, retry in {wait}s...")
                time.sleep(wait)
            else:
                raise
        except APIConnectionError as e:
            print(f"⚠️ Connection error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                raise
        except APIError as e:
            print(f"⚠️ API error {e.status_code}: {e.message}")
            raise  # 业务错误不重试
```

**常见错误**：

| 错误码 | 含义 | 处理 |
|--------|------|------|
| 400 | 请求格式错误 | 检查 skill_id、beta 头、必填字段 |
| 401 | API key 无效 | 检查环境变量 |
| 403 | 权限不足 | 申请相应 beta 权限 |
| 404 | skill_id 不存在 | 重新上传 |
| 429 | 速率限制 | 退避重试 |
| 500 | 服务端错误 | 重试 |

---

## 5.7 成本与性能考虑

### 5.7.1 成本模型

Skill 加载会增加 token 消耗：

| 阶段 | 增量 token | 是否必付 |
|------|----------|---------|
| L1 元数据 | ~100-200 / skill | **常驻**（多个 skill 累加） |
| L2 主体 | ~1,500-3,000 | 触发时付一次 |
| L3 资源 | ~500-2,000 / 文件 | 按需 |
| Code Execution | 工具调用元数据 | 每次调用 |
| 文件下载/上传 | 文件大小相关 | 按需 |

**优化**：
- 减少 L1 的 skill 数量（精简到必要的）
- 用 `disable-model-invocation` 排除不自动触发的 skill
- Code Execution 用 Haiku 模型（如果 skill 不复杂）

### 5.7.2 模型选择

| Skill 类型 | 推荐模型 |
|-----------|---------|
| 简单规则执行（PDF 填表） | Sonnet |
| 复杂分析（代码审查） | Opus |
| 大批量处理 | Sonnet |
| 思考密集型 | Opus |
| 节省成本 | Haiku（仅最简单场景） |

### 5.7.3 性能优化

- **复用 skill_id**：skill 是 immutable，上传一次反复用
- **预热**：批量任务前先空跑一次
- **并发请求**：不同任务用不同 skill_id 并发调用
- **缓存文件 ID**：同一文件多次任务可复用 file_id

---

## 5.8 常见集成模式

### 模式 1：CI/CD 中的代码审查

```python
# 在 PR 流水线里
def review_pr(repo: str, pr_id: int):
    diff = get_pr_diff(repo, pr_id)
    response = chat_with_skill(
        skill_id=CODE_REVIEW_SKILL_ID,
        user_message=f"审查这个 PR 的 diff：\n{diff}"
    )
    post_comment(repo, pr_id, response)
```

### 模式 2：客服机器人

```python
def handle_user_message(user_msg: str, context: dict):
    response = chat_with_skill(
        skill_id=CUSTOMER_SERVICE_SKILL_ID,
        user_message=user_msg,
        upload_files=[context.get("attachment")]
    )
    return response
```

### 模式 3：文档批量处理

```python
def batch_process_pdfs(pdf_paths: list):
    for path in pdf_paths:
        result = process_pdf(SKILL_ID, path, FIELDS)
        save_result(path, result)
```

### 模式 4：内部工具集成

```python
# FastAPI endpoint
@app.post("/api/fill-pdf")
async def fill_pdf_endpoint(file: UploadFile, fields: dict):
    # 保存上传文件
    tmp_path = f"/tmp/{file.filename}"
    with open(tmp_path, "wb") as f:
        f.write(await file.read())

    # 处理
    result = process_pdf(SKILL_ID, tmp_path, fields)

    # 返回结果
    return {"result": result}
```

---

## 5.9 Anthropic 内置 Skill

除了自定义 skill，Anthropic 还提供**官方内置**的 skill：

| Skill | 能力 |
|-------|------|
| Excel | 创建带公式的电子表格 |
| PowerPoint | 生成演示文稿 |
| Word | 创建 Word 文档 |
| PDF | 填写 PDF 表单 |

**使用方式**：

```python
response = client.beta.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=4096,
    betas=["code-execution-2025-01-01", "skills-2025-01-01"],
    skills=[
        {"type": "anthropic", "name": "pdf"}  # 用官方内置
    ],
    tools=[{"type": "code_execution_20250101", "name": "code_execution"}],
    messages=[...]
)
```

**注意**：内置 skill 的 `type` 是 `"anthropic"`，自定义是 `"custom"`。

---

## 5.10 接下来

- 想看 Skill 体系怎么设计（多 skill、版本、监控）→ [第 6 章 · 体系设计](./06-design.md)
- 想了解 Cursor / Claude.ai / Trae / Minimax Code 各自的 skill 体系 → [第 7 章 · 生态对照](./07-ecosystem.md)
- 触发不准或加载失败想排查 → [第 8 章 · 调试与反模式](./08-debug.md)
