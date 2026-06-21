---
name: meeting-minutes
description: |
  把会议录音/转写文本整理成结构化会议纪要。支持周会、项目复盘、客户沟通、全员会四种类型，
  自动识别会议类型并应用对应模板。当用户说"整理会议"、"会议纪要"、"整理录音"时使用。
when_to_use: |
  Use this skill when the user provides meeting transcript or notes and
  wants structured minutes. Do NOT use for: general text summarization,
  or generating meeting agendas.
paths: []
context: fork
agent: general-purpose
argument-hint: "<meeting-type> <transcript-or-file>"
---

# 会议纪要 Skill

详细文档见 [SKILL.md](../../chapters/04-writing.md#43-meeting-minutes会议纪要)

## 工作流程

### Step 1：识别会议类型

读用户提供的转写文本，根据关键词判断：

| 关键词 / 模式 | 会议类型 |
|--------------|---------|
| "上周"、"本周"、"下周"、"周会"、"weekly" | weekly |
| "做得好的"、"做得不好的"、"retro"、"复盘"、"总结" | retrospective |
| "客户"、"contract"、"合作"、"采购"、"需求" | client |
| "全员"、"all hands"、"公司"、"组织" | all-hands |

### Step 2：加载对应模板

根据类型，**只**读取对应的 reference 文件（节省 token）：

- weekly → references/weekly.md
- retrospective → references/retrospective.md
- client → references/client.md
- all-hands → references/all-hands.md

### Step 3：提取关键信息

按模板的字段，从转写文本里抽取：参会人、议题、决议、行动项、风险 / 阻塞、未决议。

### Step 4：输出

按 reference 模板的格式输出。

### Step 5：保存（可选）

询问用户是否要保存到文件。默认路径：`./minutes/YYYY-MM-DD-<meeting-type>.md`

## 关键决策点

- **文本很短**（< 200 字） → 标注"信息不完整"
- **文本超长**（> 5000 字） → 用 `context: fork` 隔离处理
- **多个会议混在一段文本** → 让用户拆分
- **没有发言人标识** → 标注"未识别发言人"

## 隐私

- **不要**把会议内容传到外部服务
- **不要**记录敏感信息（薪资、个人评价）到结构化字段
- 如有敏感信息，标注 `[已脱敏]`
