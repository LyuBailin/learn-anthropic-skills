#!/bin/bash
# batch-check.sh - 批量检查 skills 目录下所有 skill
# 用法: ./batch-check.sh <skills-root>

set -e

SKILLS_ROOT=${1:-.}

if [ ! -d "$SKILLS_ROOT" ]; then
    echo "❌ 目录不存在: $SKILLS_ROOT"
    exit 1
fi

echo "=== 批量检查: $SKILLS_ROOT ==="
echo ""

total=0
ok=0
warn=0
fail=0

for skill_dir in "$SKILLS_ROOT"/*/; do
    if [ -d "$skill_dir" ] && [ -f "$skill_dir/SKILL.md" ]; then
        total=$((total+1))
        name=$(basename "$skill_dir")
        echo "─── $name ───"

        # 复用 check-skill.sh 的逻辑
        if [ -x "./check-skill.sh" ]; then
            if ./check-skill.sh "$skill_dir" > /tmp/check_output.txt 2>&1; then
                if grep -q "⚠️" /tmp/check_output.txt; then
                    echo "⚠️ 有警告"
                    warn=$((warn+1))
                else
                    echo "✓ 通过"
                    ok=$((ok+1))
                fi
            else
                echo "❌ 失败"
                cat /tmp/check_output.txt
                fail=$((fail+1))
            fi
        else
            # 简化版检查
            if head -1 "$skill_dir/SKILL.md" | grep -q "^---$" \
               && grep -q "^name:" "$skill_dir/SKILL.md" \
               && grep -q "^description:" "$skill_dir/SKILL.md"; then
                echo "✓ 通过（基本检查）"
                ok=$((ok+1))
            else
                echo "❌ 失败"
                fail=$((fail+1))
            fi
        fi
        echo ""
    fi
done

echo "=== 总结 ==="
echo "总 skill 数: $total"
echo "  ✓ 通过: $ok"
echo "  ⚠️ 警告: $warn"
echo "  ❌ 失败: $fail"
