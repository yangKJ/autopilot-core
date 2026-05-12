---
name: skill-selector
description: |
  🎯 技能选择器 - 根据文件变更类型智能选择要执行的技能

  触发场景：
  - 说"选择技能"
  - 说"分析文件变更"
  - skill-chain 中需要根据变更选择技能时
  - auto-trigger 中需要智能选择技能时

  功能：
  - 文件模式匹配
  - 变更类型分析
  - 技能优先级排序
  - 输出技能映射

version: 1.0.0
author: mcp agent
trigger_patterns:
  - "选择技能"
  - "分析文件变更"
  - "skill selector"
  - "技能选择"
tags: [skill-selector, file-change, intelligent-selection]
---

# 🎯 Skill Selector v1.0

> 根据文件变更类型智能选择要执行的技能

## 工作原理

```
[文件列表] → [模式匹配] → [技能映射] → [优先级排序] → [输出]
```

## 文件 → 技能映射规则

| 文件模式 | 选择技能 | 优先级 |
|---------|---------|--------|
| `*.py` | test-runner, commit-validator | 高 |
| `tests/**/*.py` | test-runner | 高 |
| `server.py` | project-health-monitor, self-healing-executor | 最高 |
| `template_engine/**` | commit-validator | 中 |
| `ai_self_healing/**` | self-healing-executor, commit-validator | 高 |
| `ios_automation_core/**` | commit-validator | 中 |
| `*.json` | deployment-checker | 中 |
| `*.md` | learning-recorder | 低 |
| `.claude/skills/**` | learning-recorder | 低 |

## 使用方式

### CLI

```bash
# 基本用法
python3 .claude/skills/skill-selector/scripts/select_skills.py --files tests/test_a.py server.py

# 输出到文件
python3 .claude/skills/skill-selector/scripts/select_skills.py --files tests/test_a.py --output result.json

# 从 git diff 获取文件
python3 .claude/skills/skill-selector/scripts/select_skills.py --context-file context.json
```

### 技能选择结果

```json
{
  "skills": ["self-healing-executor", "test-runner", "commit-validator"],
  "skill_map": {
    "test-runner": ["tests/test_a.py", "server.py"],
    "commit-validator": ["server.py"]
  },
  "analysis": {
    "total_files": 2,
    "by_type": {".py": 2},
    "skills_needed": ["self-healing-executor"],
    "high_priority": ["server.py"]
  }
}
```

## 在 Skill Chain 中使用

```yaml
chain:
  name: on-change
  steps:
    - name: select-skills
      skill: skill-selector

    - name: execute
      skill: parallel-executor
      if: "select-skills.success"
```

## 输出字段

| 字段 | 说明 |
|------|------|
| `skills` | 要执行的技能列表（已排序） |
| `skill_map` | 技能 → 文件映射 |
| `analysis.total_files` | 变更文件总数 |
| `analysis.high_priority` | 高优先级文件列表 |
| `analysis.skills_needed` | 必需的技能 |
