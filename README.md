# learn-skills — 完整掌握 Anthropic Agent Skills

<div align="center">

**从零开始，系统性地理解、设计、编写、调试 Anthropic Agent Skills 机制。**

[🌐 在线阅读](https://lyubailin.github.io/learn-anthropic-skills/) ·
[📖 章节目录](#怎么读) ·
[🚀 示例](#配套示例) ·
[💡 资料](#资料来源)

</div>

---

> **本项目包含**：
> - 📘 8 章系统教程（覆盖概念 / 编写 / API / 体系设计 / 调试）
> - 🛠️ 4 个完整可运行 Skill 示例（PDF / 代码审查 / 会议纪要 / API 集成）
> - 🌐 9 个深色主题 HTML 页面（双击 `site/index.html` 即可阅读）
> - 🔧 md → html 转换脚本（编辑 md 后一键重建）

---

## 这份文档适合谁

- **用过 system prompt / tool calling**，想知道 Skill 跟它们什么关系
- 想在 **Claude Code / Claude API / Minimax Code** 里编写自己的 Skill
- 想设计 **企业级 Skill 体系**（多 Skill 协同、版本管理、与 MCP 配合）
- 想搞懂"按需加载"这套机制 **背后到底在发生什么**

---

## 怎么读

按章节顺序读最省力，但**每一章都自包含**——你也可以跳着读。

> 🌐 **网页阅读**：所有章节已转成独立的 HTML 页面（深色主题 + 代码高亮 + 左侧 TOC）。**推荐双击 `site/index.html` 打开浏览**。

| 章节 | Markdown | HTML（推荐） | 主题 | 时长 |
|------|----------|-------------|------|------|
| [第 1 章 · 概念入门](./chapters/01-concept.md) | [📄 md](./chapters/01-concept.md) | [🌐 html](./site/01-concept.html) | 什么是 Skill、跟 system prompt / tool / sub-agent 区别 | 15 min |
| [第 2 章 · 文件解剖](./chapters/02-anatomy.md) | [📄 md](./chapters/02-anatomy.md) | [🌐 html](./site/02-anatomy.html) | SKILL.md、frontmatter、资源文件全解 | 25 min |
| [第 3 章 · 加载机制](./chapters/03-loading.md) | [📄 md](./chapters/03-loading.md) | [🌐 html](./site/03-loading.html) | 三层加载、token 经济性、触发决策 | 20 min |
| [第 4 章 · 实战编写](./chapters/04-writing.md) | [📄 md](./chapters/04-writing.md) | [🌐 html](./site/04-writing.html) | 4 个完整可运行 Skill 案例 | 40 min |
| [第 5 章 · API 集成](./chapters/05-api.md) | [📄 md](./chapters/05-api.md) | [🌐 html](./site/05-api.html) | Messages API + Files API + SDK | 30 min |
| [第 6 章 · 体系设计](./chapters/06-design.md) | [📄 md](./chapters/06-design.md) | [🌐 html](./site/06-design.html) | 多 Skill 架构、版本、命名空间、监控 | 30 min |
| [第 7 章 · 生态对照](./chapters/07-ecosystem.md) | [📄 md](./chapters/07-ecosystem.md) | [🌐 html](./site/07-ecosystem.html) | Minimax Code / Cursor / Claude.ai / Trae | 20 min |
| [第 8 章 · 调试与反模式](./chapters/08-debug.md) | [📄 md](./chapters/08-debug.md) | [🌐 html](./site/08-debug.html) | 不触发、误触发、性能问题、调试手法 | 20 min |

---

## 配套示例

所有示例都放在 [`examples/`](./examples/) 下，可以直接复制到 `~/.claude/skills/` 或项目 `.claude/skills/` 使用。

| 示例 | 主题 | 难度 |
|------|------|------|
| [pdf-form-filler](./examples/pdf-form-filler/) | 官方经典：PDF 表单提取与填写 | ⭐⭐ |
| [code-review](./examples/code-review/) | git 集成 + 多文件 diff 审查 | ⭐⭐⭐ |
| [meeting-minutes](./examples/meeting-minutes/) | 中文场景：多会议类型 + context: fork | ⭐⭐⭐ |
| [api-skill-python](./examples/api-skill-python/) | Python SDK 端到端集成 | ⭐⭐⭐⭐ |

---

## 关键事实速查（不需要通读也能上手）

- **Skill 是什么**：一份放在文件夹里的 `SKILL.md`（YAML 头 + Markdown 主体），Claude 启动时只把 `name + description` 注入上下文，匹配时再读主体
- **三层加载**：L1 元数据（始终在）→ L2 主体（按需）→ L3 资源（按需）
- **目录**：`my-skill/SKILL.md` + 可选 `scripts/` `references/` `assets/`
- **frontmatter 必备**：`name` + `description`
- **触发**：自动（description 语义匹配）或手动（`/skill-name`）
- **作用域**：企业 > 个人 > 项目 > 插件
- **一句话总结**：Skill = 给 AI 的"操作手册 + 工具箱"，按需加载、节省 token、稳定行为

---

## 资料来源

- 官方文档：<https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview>
- 工程博客：<https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills>
- 官方代码：<https://github.com/anthropics/skills>
- Claude Code 文档：<https://code.claude.com/docs/en/skills>
- 开放标准：<https://agentskills.io>

> 整理时间：2026-06-16。Skill 机制仍在演进，**请以官方文档为准**。

---

## License

本仓库为学习/教学目的整理，示例代码以 MIT 协议发布。
引用官方内容遵循 Anthropic 公开资料的使用规则。详见 [LICENSE](./LICENSE)。
