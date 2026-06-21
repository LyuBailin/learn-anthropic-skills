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

## 常见问题

### Q: 填写后字段值不显示？

A: 多数 PDF 需要先 `update_page_form_field_values` 再重新生成。

### Q: signature 字段无法填写？

A: 数字签名是图像，程序无法直接添加。

### Q: 字段名带特殊字符？

A: 用 JSON 配置文件传字段，避免命令行参数解析问题。

## 进阶用法

- **批量填写**：用 JSON 文件传字段
- **模板化**：保存常用填写模板
- **验证规则**：添加字段值校验（邮箱格式、电话格式）
