#!/bin/bash
# pre-commit hook for commit-validator

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

# 切换到项目根目录
cd "$SCRIPT_DIR/../../.." 2>/dev/null || cd "$(git rev-parse --show-toplevel)"

# 运行验证器
python3 "$SKILL_DIR/commit-validator/scripts/validate.py"
exit $?