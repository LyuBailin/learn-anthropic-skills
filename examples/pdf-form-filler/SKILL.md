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

详细文档见 [SKILL.md](../../chapters/04-writing.md#41-pdf-form-fillerpdf-表单填写)
