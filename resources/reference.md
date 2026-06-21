# 附录 · 参考资源 & 进阶阅读

> 这一章汇总：官方一手资料、社区资源、工具脚本、术语表。

---

## A.1 官方一手资料

### Anthropic 官方

| 资料 | 链接 | 用途 |
|------|------|------|
| Skills 介绍 | <https://www.anthropic.com/news/skills> | 公告原文 |
| 工程博客 | <https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills> | 深入设计原理 |
| 官方文档 | <https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview> | API / 规范 |
| 官方代码 | <https://github.com/anthropics/skills> | 16+ 官方示例 |
| Cookbook | <https://github.com/anthropics/claude-cookbooks/tree/main/skills> | 实战案例 |
| Claude Code 文档 | <https://code.claude.com/docs/en/skills> | Claude Code skill |
| Subagents 文档 | <https://code.claude.com/docs/en/sub-agents> | Sub-agent 体系 |

### Anthropic SDK

- Python: `pip install anthropic`
- TypeScript: `npm install @anthropic-ai/sdk`
- Claude Code SDK: `npm install -g @anthropic-ai/claude-code` 或 `pip install claude-code-sdk`

### Claude API 文档

- API 概览: <https://docs.anthropic.com/>
- 端点: `/v1/skills`, `/v1/files`, `/v1/messages`
- Beta 头: `skills-2025-01-01`, `files-api-2025-04-14`, `code-execution-2025-01-01`

---

## A.2 开放标准

- **Agent Skills 开放标准**: <https://agentskills.io>
- 规范包含：
  - SKILL.md 格式
  - frontmatter 字段
  - 加载机制
  - 跨平台兼容性

---

## A.3 社区资源

### 中文社区

- 公众号「AGI Hunt」：实时 AI 资讯
- 知乎专栏「Anthropic Agent Skills」主题
- 掘金、博客园、CSDN 上有大量实战文章

### GitHub 热门仓库

- `anthropics/skills`（官方）
- `ComposioHQ/awesome-claude-skills`（社区精选）
- `affaan-m/everything-claude-code`（183K ⭐）
- `sickn33/antigravity-awesome-skills`（38K ⭐，1400+ skill）
- `wshobson/agents`（35K ⭐，多 agent 编排）

### 视频教程

- DeepLearning.AI 课程：Agent Skills with Anthropic
- YouTube 搜索："Agent Skills tutorial"

---

## A.4 术语表

| 术语 | 含义 |
|------|------|
| **Skill** | 一组包含指令、脚本、资源的文件夹，Claude 按需加载 |
| **Agent Skills** | Anthropic 2025-10 发布的开放标准 |
| **SKILL.md** | Skill 的入口文件，包含 YAML frontmatter + Markdown 主体 |
| **Frontmatter** | SKILL.md 顶部的 YAML 元数据 |
| **Progressive Disclosure** | 渐进式披露：L1 元数据 → L2 主体 → L3 资源 |
| **L1 / L2 / L3** | 三层加载的层级 |
| **Description** | Skill 的触发描述，Claude 据此判断是否调用 |
| **when_to_use** | 补充的触发条件（自然语言） |
| **paths** | 路径过滤，限定 Skill 适用范围 |
| **allowed-tools** | 工具白名单 |
| **disable-model-invocation** | 只允许用户手动触发 |
| **user-invocable** | 只允许 Claude 自动触发 |
| **argument-hint** | / 命令参数补全提示 |
| **context: fork** | 在 sub-agent 隔离上下文中运行 |
| **MCP** | Model Context Protocol，连接外部工具的协议 |
| **Sub-agent** | 子智能体，独立 LLM 实例 |
| **system prompt** | 系统提示，始终加载 |
| **system prompt vs Skill** | 始终加载 vs 按需加载 |
| **skill vs tool** | 行为规范 vs 动作调用 |
| **skill vs sub-agent** | 无 LLM 函数 vs LLM 智能体 |
| **CLAUDE.md** | Claude Code 项目级上下文文件 |
| **Files API** | Anthropic API 上传 / 下载文件 |
| **Code Execution Tool** | 沙箱执行环境，Skill "能干活"的前提 |
| **L1 budget** | L1 元数据常驻的字符预算（约 2% 上下文窗口） |

---

## A.5 实用工具脚本

### check-skill.sh

```bash
#!/bin/bash
# 用法: ./check-skill.sh <skill-dir>
SKILL_DIR=${1:-.}

echo "=== Skill 自检: $SKILL_DIR ==="

# 1. SKILL.md 存在
[ -f "$SKILL_DIR/SKILL.md" ] || { echo "❌ SKILL.md 不存在"; exit 1; }

# 2. frontmatter
head -1 "$SKILL_DIR/SKILL.md" | grep -q "^---$" || {
    echo "❌ SKILL.md 缺少 YAML frontmatter"; exit 1;
}

# 3. 必填字段
grep -q "^name:" "$SKILL_DIR/SKILL.md" || {
    echo "❌ 缺少 name 字段"; exit 1;
}
grep -q "^description:" "$SKILL_DIR/SKILL.md" || {
    echo "❌ 缺少 description 字段"; exit 1;
}

# 4. 解析 YAML
python3 -c "
import yaml
content = open('$SKILL_DIR/SKILL.md').read()
parts = content.split('---', 2)
if len(parts) < 3:
    print('❌ frontmatter 格式错误')
    exit(1)
meta = yaml.safe_load(parts[1])
required = ['name', 'description']
for key in required:
    if key not in meta:
        print(f'❌ 缺 {key} 字段')
        exit(1)
print('✓ YAML 格式正确')
print(f'  name: {meta[\"name\"]}')
print(f'  description 长度: {len(meta[\"description\"])} 字符')
"

echo "✓ 自检通过"
```

### skill-stats.sh

```bash
#!/bin/bash
# 用法: ./skill-stats.sh <skill-dir>
# 报告 skill 的各种统计
SKILL_DIR=${1:-.}

echo "=== Skill 统计: $SKILL_DIR ==="
echo "--- 主体大小 ---"
wc -l "$SKILL_DIR/SKILL.md"
echo "--- frontmatter ---"
head -10 "$SKILL_DIR/SKILL.md"
echo "--- 资源文件 ---"
find "$SKILL_DIR" -type f \( -name "*.md" -o -name "*.py" -o -name "*.sh" \) | sort
echo "--- 文件统计 ---"
echo "Markdown 文件: $(find "$SKILL_DIR" -name "*.md" | wc -l)"
echo "Python 脚本: $(find "$SKILL_DIR" -name "*.py" | wc -l)"
echo "Shell 脚本: $(find "$SKILL_DIR" -name "*.sh" | wc -l)"
```

### batch-check.sh

```bash
#!/bin/bash
# 用法: ./batch-check.sh <skills-root>
# 检查目录下所有 skill
SKILLS_ROOT=${1:-~/.claude/skills}

echo "=== 批量检查: $SKILLS_ROOT ==="
total=0
ok=0

for skill_dir in "$SKILLS_ROOT"/*/; do
    if [ -f "$skill_dir/SKILL.md" ]; then
        total=$((total+1))
        echo -n "  $(basename "$skill_dir"): "
        if ./check-skill.sh "$skill_dir" > /dev/null 2>&1; then
            echo "✓"
            ok=$((ok+1))
        else
            echo "❌"
        fi
    fi
done

echo ""
echo "总结: $ok / $total 通过"
```

---

## A.6 速查卡

### frontmatter 速查

```yaml
---
# 必填
name: my-skill                       # 小写 + 连字符，≤64
description: "..."                   # ≤1024 字符，触发描述

# 推荐
when_to_use: "..."                   # 补充触发
paths: ["src/**/*.ts"]               # 路径过滤
allowed-tools: [Read, Bash(python *)] # 工具白名单
argument-hint: "[file]"              # / 命令提示

# 高级
disable-model-invocation: false      # 禁止 Claude 自动
user-invocable: true                 # 允许用户手动
model: sonnet                        # 模型覆盖
effort: high                         # 思考深度
context: fork                        # sub-agent 隔离
agent: Explore                       # sub-agent 类型
hooks:                               # 生命周期钩子
  PreToolUse:
    - matcher: "Bash"
      hooks: [{type: command, command: "./validate.sh"}]
shell: bash                          # shell 类型
---
```

### 三层加载速查

| 层 | 内容 | 时机 | 大小 |
|----|------|------|------|
| L1 | name + description | 启动 | ~100 词 |
| L2 | SKILL.md 主体 | 匹配 | < 500 行 |
| L3+ | scripts/references/ | 按需 | 不限 |

### 作用域优先级

企业 > 个人 > 项目 > 插件

### 触发方式

- 自动：description + when_to_use + paths 语义匹配
- 手动：`/skill-name` 或 `/skill-name arg1 arg2`

---

## A.7 常见问题 FAQ

### Q: 装 100 个 skill 会撑爆上下文吗？

A: 不会。每个 skill 的 L1 元数据约 100 词，100 个 skill 共 1 万词 ≈ 6.5% 上下文窗口。但触发时 L2 主体（~2K-3K）会按需加载。

### Q: Skill 和 System Prompt 怎么分工？

A: 简短、高频的规则放 system prompt；详细、低频的流程放 skill。

### Q: Skill 能调用其他 skill 吗？

A: 不能直接调用，但可以在主体里提示 Claude 使用其他 skill（"完成后用 /security-scan 深入检查"）。

### Q: Skill 能修改其他 skill 吗？

A: 主体里可以描述修改流程，但具体操作要通过 Bash 工具执行（用户授权）。

### Q: description 字符限制是硬性还是建议？

A: 软限制。超过 1536 字符（包括 when_to_use）会被截断。L1 常驻 token 预算约上下文窗口的 2%。

### Q: 怎么知道哪些 skill 在用？

A: 监控 Claude Code 日志 `/var/log/claude-code`（具体路径看平台）。

### Q: Skill 跨平台能通用吗？

A: 大部分通用。差异主要在高级字段（hooks、agent、context: fork）。详见 [第 7 章 · 生态对照](./07-ecosystem.md)。

### Q: Skill 能用 LLM 吗？

A: 脚本本身不能用 LLM（脚本是无 LLM 的纯函数）。但 Claude 在调用 skill 时会用 LLM 理解主体并决策。

### Q: 怎么调试触发问题？

A: 详见 [第 8 章 · 调试与反模式](./08-debug.md)。

### Q: Skill 升级怎么处理？

A: 通过 Skills API 的版本管理。客户端用 `version: "latest"` 或锁定版本号。生产环境建议锁定版本。

---

## A.8 进一步探索

### 推荐阅读顺序

1. 先看 [第 1 章 · 概念入门](./01-concept.md) —— 建立心智模型
2. 再看 [第 2 章 · 文件解剖](./02-anatomy.md) —— 学会写 SKILL.md
3. 看 [第 3 章 · 加载机制](./03-loading.md) —— 理解内部
4. 动手：照 [第 4 章 · 实战编写](./04-writing.md) 复制示例
5. 进阶：看 [第 5 章 · API 集成](./05-api.md)
6. 体系化：看 [第 6 章 · 体系设计](./06-design.md)
7. 跨平台：看 [第 7 章 · 生态对照](./07-ecosystem.md)
8. 遇到问题：看 [第 8 章 · 调试与反模式](./08-debug.md)

### 练习项目

1. **把现在用的 system prompt 改造为 skill**——看哪些值
2. **复制 4 个示例 skill 到 ~/.claude/skills/**——亲手触发
3. **写一个团队专属的 code-review skill**——协作场景
4. **用 Anthropic API 集成到自己的应用**——生产场景
5. **设计一个 10 个 skill 的小体系**——架构思维

### 进阶主题

- 自适应 skill（根据对话历史调整行为）
- Skill A/B 测试（不同 description 对比效果）
- Skill 可观测性平台（自建监控）
- Skill 市场（团队内部分发）

---

## A.9 项目维护

### 如何贡献

欢迎补充：
- 新的实战示例
- 跨平台迁移经验
- 性能优化案例
- 反模式补充

### 版本

- v1.0 (2026-06-16) — 初版

### License

本仓库为学习/教学目的整理，示例代码以 MIT 协议发布。引用官方内容遵循 Anthropic 公开资料的使用规则。
