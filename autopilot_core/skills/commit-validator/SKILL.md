---
name: commit-validator
description: |
  ✅ 提交验证器技能 - git commit 前自动运行 lint + 测试，确保代码质量

  触发场景：
  - git commit 时自动触发（pre-commit hook）
  - 说"验证提交"
  - 说"检查代码质量"
  - 说"commit 前的检查"
  - pre-commit hook 配置

  功能：
  - 运行 ruff lint 检查
  - 运行快速测试
  - 失败时阻断提交
  - 成功时显示检查通过
  - 可配置跳过某些检查

version: 1.0.0
author: mcp agent
trigger_patterns:
  - "验证提交"
  - "检查代码质量"
  - "commit 前的检查"
  - "pre-commit"
tags: [git, commit, lint, testing, pre-commit, validation]
---

# ✅ Commit Validator v1.0

> git commit 前自动质量门禁

## 工作流程

```
git commit
    ↓
pre-commit hook → commit-validator
    ↓
┌─────────────────────────────────────┐
│ 1. Ruff Lint                        │
│ 2. Quick Tests                       │
│ 3. (optional) Coverage Check         │
└─────────────────────────────────────┘
    ↓
✅ All Pass → 允许提交
❌ Any Fail → 阻断提交 + 显示错误
```

## 使用方式

### 1. 安装 pre-commit hook

```bash
# 创建 hook 链接
ln -sf .claude/skills/commit-validator/scripts/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# 或使用 install 命令
python .claude/skills/commit-validator/scripts/install.py
```

### 2. 手动触发

```bash
python .claude/skills/commit-validator/scripts/validate.py
```

### 3. 跳过检查（临时）

```bash
git commit --no-verify  # 跳过所有检查
SKIP_LINT=1 git commit   # 跳过 lint
SKIP_TEST=1 git commit    # 跳过测试
```

## 配置

在 `scripts/config.py` 中修改：

```python
CONFIG = {
    "lint": {
        "enabled": True,
        "command": "ruff check . --select E,F,W --ignore PGH,INP",
        "fail_on_error": True
    },
    "test": {
        "enabled": True,
        "mode": "quick",           # quick / full
        "fail_fast": True
    },
    "coverage": {
        "enabled": False,
        "min_percent": 80
    },
    "block_on_failure": True       # 失败时阻断提交
}
```

## 输出示例

### 通过

```
✅ Commit Validation Passed
├── 🧹 Lint:      ✅ PASS
├── 🧪 Test:      ✅ 1071 passed (111s)
└── ⏱️ Duration:  115s

Ready to commit!
```

### 失败

```
❌ Commit Validation Failed
├── 🧹 Lint:      ❌ 3 errors
│   └── view: .claude/skills/agent-council/SKILL.md:127
├── 🧪 Test:      ✅ PASS
└── ⏱️ Duration:  120s

Fix errors before committing.
Run: ruff check . --fix
```

## 状态码

| 状态码 | 含义 |
|--------|------|
| 0 | 验证通过，可以提交 |
| 1 | 验证失败，阻断提交 |
| 2 | 配置错误 |
| 3 | 超时 |

## 集成到其他项目

```bash
# 复制技能到目标项目
cp -r .claude/skills/commit-validator /path/to/project/.claude/skills/

# 安装 hook
cd /path/to/project
python .claude/skills/commit-validator/scripts/install.py
```

## Skip 机制

| 环境变量 | 效果 |
|---------|------|
| `SKIP_LINT=1` | 跳过 lint 检查 |
| `SKIP_TEST=1` | 跳过测试 |
| `SKIP_ALL=1` | 跳过所有检查 |
| `FORCE=1` | 强制通过（不推荐） |