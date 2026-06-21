# API Skill Python 集成示例

演示如何用 Anthropic Python SDK 集成自定义 Skill 到自己的应用。

## 完整文档

详细说明见 [chapters/04-writing.md § 4.4](../../chapters/04-writing.md#44-api-skill-pythonapi-集成)

## 安装

```bash
pip install anthropic python-dotenv
```

## 配置

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

## 运行

```bash
python api_skill_demo.py
```

## 核心流程

```
┌──────────────────┐
│ 1. 打包 Skill    │  zip 压缩 skill 目录
└────────┬─────────┘
         ↓
┌──────────────────┐
│ 2. 上传 Skill    │  client.beta.skills.create()
└────────┬─────────┘
         ↓
┌──────────────────┐
│ 3. 上传文件      │  client.beta.files.upload()
└────────┬─────────┘
         ↓
┌──────────────────┐
│ 4. 构造消息      │  含 file_id + 文本
└────────┬─────────┘
         ↓
┌──────────────────┐
│ 5. 调用 API      │  messages.create() with skills=[]
│   （含 code exec）│  tools=[code_execution_20250101]
└────────┬─────────┘
         ↓
┌──────────────────┐
│ 6. 处理响应      │  文本 + 沙箱生成文件
└────────┬─────────┘
         ↓
┌──────────────────┐
│ 7. 下载输出      │  client.beta.files.download()
└──────────────────┘
```

## 需要的 Beta 头

- `code-execution-2025-01-01` — Code Execution Tool
- `skills-2025-01-01` — Skills API
- `files-api-2025-04-14` — Files API

## 关键 API

| 用途 | 调用 |
|------|------|
| 创建 Skill | `client.beta.skills.create(name, skill_data)` |
| 列出 Skill | `client.beta.skills.list()` |
| 查看版本 | `client.beta.skills.versions.list(skill_id)` |
| 删除 Skill | `client.beta.skills.delete(skill_id)` |
| 上传文件 | `client.beta.files.upload(file)` |
| 下载文件 | `client.beta.files.download(file_id)` |
| 发送消息 | `client.beta.messages.create(skills=..., tools=...)` |
| 流式发送 | `client.beta.messages.stream(...)` |

## 注意事项

1. **Skill 必须打包成 zip** 上传，不能传目录
2. **Code Execution 是 skill 能"干活"的前提**——没它 Claude 只能读不能执行
3. **文件 ID 是临时的**——会话结束就失效，需要时及时下载
4. **Beta API 可能有变**——生产环境请锁定 SDK 版本
