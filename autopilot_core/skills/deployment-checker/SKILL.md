---
name: deployment-checker
description: |
  🚀 部署检查器技能 - 部署前自动验证项目状态、依赖、环境、风险评估

  触发场景：
  - 说"部署前检查"
  - 说"检查部署就绪"
  - 说"deployment check"
  - 说"发布前验证"
  - CI/CD 管道中的部署阶段

  功能：
  - 依赖完整性检查
  - 环境变量验证
  - 代码完整性检查
  - 风险评估
  - 部署清单生成

version: 1.0.0
author: mcp agent
trigger_patterns:
  - "部署前检查"
  - "检查部署就绪"
  - "deployment check"
  - "发布前验证"
tags: [deployment, pre-deploy, validation, risk-assessment]
---

# 🚀 Deployment Checker v1.0

> 部署前的最后一道门禁

## 工作流程

```
[部署触发]
    ↓
┌─────────────────────────────────────┐
│ 1. Dependency Check                 │
│    - 依赖是否完整                   │
│    - 版本是否兼容                   │
│    - 冲突检测                       │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 2. Environment Validation          │
│    - 必需的环境变量                 │
│    - 密钥/证书是否存在              │
│    - 配置完整性                     │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 3. Code Integrity                  │
│    - 代码是否完整                   │
│    - 无未提交的敏感文件             │
│    - 无调试代码                     │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ 4. Risk Assessment                 │
│    - 安全风险                       │
│    - 性能风险                       │
│    - 兼容性风险                     │
└─────────────────────────────────────┘
    ↓
[部署清单 / 阻断报告]
```

## 检查项清单

| 检查项 | 通过条件 | 严重性 |
|--------|---------|--------|
| 依赖完整 | `pip freeze` 与 `requirements.txt` 一致 | 🔴 阻断 |
| 环境变量 | 所有 `REQUIRED_*` 变量已设置 | 🔴 阻断 |
| 代码完整 | 无未提交的 critical 文件 | 🟡 警告 |
| 安全扫描 | 无 `password`, `secret` 硬编码 | 🔴 阻断 |
| 性能基线 | 启动时间 < 5s | 🟡 警告 |
| 测试覆盖 | 测试覆盖率 > 70% | 🟡 警告 |

## 使用方式

### 手动触发

```bash
python3 .claude/skills/deployment-checker/scripts/check.py
```

### 详细模式

```bash
python3 .claude/skills/deployment-checker/scripts/check.py --verbose
```

### 仅快速检查

```bash
python3 .claude/skills/deployment-checker/scripts/check.py --quick
```

## 输出示例

### 通过

```
🚀 Deployment Readiness Check
==================================================

✅ Dependency Check     - All dependencies resolved
✅ Environment Check    - All required env vars set
✅ Code Integrity       - No uncommitted secrets
⚠️  Security Scan        - 2 potential issues found (warnings)
✅ Risk Assessment      - Low risk

==================================================
✅ READY TO DEPLOY

Deployment checklist:
- [x] Dependencies verified
- [x] Environment configured
- [x] No security blockers
- [x] Low risk assessment
```

### 失败

```
❌ DEPLOYMENT BLOCKED

Blocking issues:
🔴 Environment: OPENAI_API_KEY not set
🔴 Security: Hardcoded password found in config.py:42

Fix before deploying:
1. Set OPENAI_API_KEY environment variable
2. Remove hardcoded password from config.py
```

## 状态码

| 状态码 | 含义 |
|--------|------|
| 0 | 部署就绪 |
| 1 | 存在阻断问题 |
| 2 | 检查执行错误 |
| 3 | 超时 |

## 配置

在 `scripts/config.py` 中修改：

```python
CONFIG = {
    "required_env_vars": ["OPENAI_API_KEY", "DATABASE_URL"],
    "security_scan": True,
    "min_coverage": 70,
    "max_startup_time": 5,  # seconds
    "block_on_warnings": False
}
```

## CI/CD 集成

```yaml
# .github/workflows/deploy.yml
- name: Deployment Check
  run: |
    python3 .claude/skills/deployment-checker/scripts/check.py
```