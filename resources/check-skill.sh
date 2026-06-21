#!/bin/bash
# check-skill.sh - 检查一个 skill 目录的格式正确性
# 用法: ./check-skill.sh <skill-dir>

set -e

SKILL_DIR=${1:-.}

if [ ! -d "$SKILL_DIR" ]; then
    echo "❌ 目录不存在: $SKILL_DIR"
    exit 1
fi

echo "=== Skill 自检: $SKILL_DIR ==="

# 1. SKILL.md 存在
if [ ! -f "$SKILL_DIR/SKILL.md" ]; then
    echo "❌ SKILL.md 不存在"
    exit 1
fi
echo "✓ SKILL.md 存在"

# 2. frontmatter 格式
if ! head -1 "$SKILL_DIR/SKILL.md" | grep -q "^---$"; then
    echo "❌ SKILL.md 缺少 YAML frontmatter（应以 --- 开头）"
    exit 1
fi
echo "✓ frontmatter 存在"

# 3. 必填字段
if ! grep -q "^name:" "$SKILL_DIR/SKILL.md"; then
    echo "❌ 缺少 name 字段"
    exit 1
fi
if ! grep -q "^description:" "$SKILL_DIR/SKILL.md"; then
    echo "❌ 缺少 description 字段"
    exit 1
fi
echo "✓ 必填字段完整"

# 4. YAML 解析
if command -v python3 &> /dev/null; then
    python3 -c "
import yaml, sys
with open('$SKILL_DIR/SKILL.md') as f:
    content = f.read()
parts = content.split('---', 2)
if len(parts) < 3:
    print('❌ frontmatter 格式错误（应被 --- 包围）')
    sys.exit(1)
try:
    meta = yaml.safe_load(parts[1])
except yaml.YAMLError as e:
    print(f'❌ YAML 解析错误: {e}')
    sys.exit(1)
required = ['name', 'description']
for key in required:
    if key not in meta:
        print(f'❌ 缺 {key} 字段')
        sys.exit(1)
print('✓ YAML 格式正确')
print(f'  name: {meta[\"name\"]}')
print(f'  description 长度: {len(str(meta[\"description\"]))} 字符')
" || exit 1
else
    echo "⚠️ python3 未安装，跳过 YAML 解析验证"
fi

# 5. 主体长度
BODY_LINES=$(awk '/^---$/{c++; next} c==2' "$SKILL_DIR/SKILL.md" | wc -l)
if [ "$BODY_LINES" -gt 500 ]; then
    echo "⚠️ 主体较长（$BODY_LINES 行），建议拆 reference"
else
    echo "✓ 主体长度合理（$BODY_LINES 行）"
fi

# 6. 脚本可执行
if [ -d "$SKILL_DIR/scripts" ]; then
    find "$SKILL_DIR/scripts" -name "*.py" -o -name "*.sh" | while read f; do
        if [ ! -x "$f" ]; then
            echo "⚠️ $f 不可执行（可运行 chmod +x $f）"
        fi
    done
fi

echo ""
echo "✅ 自检完成"
