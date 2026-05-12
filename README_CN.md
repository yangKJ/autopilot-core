# Autopilot Core

> 🤖 通用自动驾驶模式 — 让任何项目拥有智能调度 + 学习预测 + 闭环自愈能力

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/packs/autopilot-core?style=social)](https://github.com/packs/autopilot-core)

**Autopilot Core** 是一个基于 Claude Code 的通用智能调度系统，将复杂的自动化工作流封装为简单的 CLI 命令。只需 `autopilot run`，系统会自动完成：技能选择 → 执行计划 → 验证 → 记录 → 通知。

---

## 目录

- [✨ 特性](#-特性)
- [🚀 快速开始](#-快速开始)
- [📖 详细指南](#-详细指南)
- [🧩 技能系统](#-技能系统)
- [⚙️ 配置系统](#-配置系统)
- [📊 学习引擎](#-学习引擎)
- [🔧 CLI 命令](#-cli-命令)
- [🔗 协同外部 CLI](#-协同外部-cli)
- [🧪 开发指南](#-开发指南)
- [❓ FAQ](#-faq)
- [📦 发行说明](#-发行说明)
- [⚠️ 已知限制](#-已知限制)

---

## ✨ 特性

### 核心能力

| 特性 | 说明 |
|------|------|
| **🎯 智能调度** | 5步闭环：技能选择 → 执行计划 → 验证 → 学习记录 → 通知 |
| **📈 自学习引擎** | SQLite 持久化 + 时间序列预测，越用越聪明 |
| **🔄 闭环自愈** | 自动检测、分类、修复、验证失败 |
| **⚙️ 分层配置** | 全局/项目/本地三层覆盖，开箱即用 |
| **🧩 11种内置技能** | 覆盖测试、验证、修复、监控、通知全流程 |
| **🌐 MCP 协议** | 原生支持 MCP Server，可接入 AI Agents |
| **⚡ 高性能** | 并行执行 + 自适应重试 + 智能超时 |
| **🔌 零依赖核心** | 核心仅需 Python 3.8+，无沉重依赖 |

### 适用场景

- 🏭 **CI/CD 集成** — 提交代码自动触发测试/验证/部署
- 🔍 **Code Review 自动化** — 每次提交自动检查代码质量
- 🐛 **Self-Healing** — 自动修复常见的测试失败和构建错误
- 📊 **项目健康监控** — 持续跟踪代码库健康状态
- 🤖 **MCP Agent 赋能** — 为 AI Agent 提供自动化执行能力

---

## 🚀 快速开始

### 安装

#### 方式 1: pip 安装（推荐）

```bash
pip install autopilot-core
```

#### 方式 2: 源码安装

```bash
git clone https://github.com/packs/autopilot-core.git
cd autopilot-core
pip install -e .
```

#### 方式 3: Homebrew（macOS）

```bash
brew install autopilot-core
```

### 初始化项目

```bash
# 进入目标项目
cd /path/to/your-project

# 初始化 autopilot 配置
autopilot init
```

`autopilot init` 会创建以下结构：

```
your-project/
├── .autopilot.yaml          # 项目配置（可提交到 git）
├── .autopilot/              # 运行时目录
│   ├── skills/              # 技能目录（11个内置技能）
│   ├── state/               # 状态文件、执行计划
│   └── .learning.db         # 学习数据库
└── .gitignore               # 自动添加 .autopilot/ 到 .gitignore
```

### 首次运行

```bash
# 查看状态
autopilot status

# 运行自动驾驶（处理所有 git 变更文件）
autopilot run

# 指定文件运行
autopilot run -f server.py tests/

# 查看监控面板
autopilot dashboard
```

---

## 📖 详细指南

### 工作原理

Autopilot Core 的核心是一个 **5 步闭环执行框架**：

```
┌─────────────────────────────────────────────────────────────────┐
│                    自动驾驶调度中心                               │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Step 1   │───▶│ Step 2   │───▶│ Step 3   │───▶│ Step 4   │  │
│  │ 技能选择  │    │ 执行计划  │    │ 验证结果  │    │ 记录学习  │  │
│  │          │    │          │    │          │    │          │  │
│  │ • 文件   │    │ • 并行   │    │ • 语法   │    │ • 模式   │  │
│  │   类型   │    │   执行   │    │   检查   │    │   分析   │  │
│  │ • 风险   │    │ • 重试   │    │ • 业务   │    │ • 预测   │  │
│  │   评估   │    │ • 超时   │    │   验证   │    │   更新   │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│        │              │              │              │            │
│        └──────────────┴──────────────┴──────────────┘            │
│                            │                                    │
│                     ┌──────┴──────┐                             │
│                     │   Step 5    │                             │
│                     │   发送通知   │                             │
│                     └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

### 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户层                                   │
│                    CLI / MCP Server                             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                       调度层 (autonomous.py)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ SkillRegistry│  │PlanGenerator│  │   ClosedLoopHealer    │  │
│  │ 技能注册表   │  │  计划生成器  │  │     闭环自愈器          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                       技能层 (skills/)                            │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │
│  │ skill- │ │  auto- │ │ parallel│ │  test- │ │commit- │        │
│  │selector│ │trigger │ │executor│ │ runner │ │validator│        │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘        │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │
│  │self-   │ │project-│ │deploy- │ │learning│ │notifi- │        │
│  │healing │ │health  │ │ment    │ │recorder│ │cation  │        │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘        │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                     学习层 (learning_engine.py)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  SQLite DB   │  │  预测引擎    │  │    趋势分析          │   │
│  │  持久化存储  │  │  时间序列    │  │    风险评估          │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 文件结构

```
autopilot_core/
├── cli.py                          # 🎯 CLI 入口（所有命令）
├── __init__.py
│
├── core/                           # 核心模块
│   ├── __init__.py
│   ├── autonomous.py               # 🚗 自动驾驶调度中心
│   ├── learning_engine.py          # 📈 学习引擎 + 预测
│   ├── config.py                  # ⚙️ 分层配置系统
│   ├── auto_heal.py               # 🔄 闭环自愈
│   ├── dashboard.py               # 📊 监控面板
│   ├── daemon.py                  # 🕐️ 持续监控守护进程
│   ├── scheduler.py               # ⏰ 定时任务调度
│   ├── git_hooks.py               # 🪝 Git Hooks 集成
│   └── nlp.py                     # 💬 自然语言接口
│
├── skills/                         # 🧩 内置技能包
│   ├── skill-selector/             # 📋 技能选择器
│   ├── auto-trigger/              # ⚡ 自动触发器
│   ├── skill-chain/                # 🔗 技能链编排
│   ├── parallel-executor/          # ⚡ 并行执行器
│   ├── test-runner/               # 🧪 测试运行器
│   ├── commit-validator/          # ✅ 提交验证器
│   ├── self-healing-executor/      # 🔧 自愈执行器
│   ├── project-health-monitor/     # 🏥 项目健康监控
│   ├── deployment-checker/         # 🚀 部署检查器
│   ├── learning-recorder/          # 📝 学习记录器
│   └── notification-hub/           # 📱 通知中心
│
└── mcp/                            # 🌐 MCP Server
    └── server.py                  # MCP 协议适配层
```

---

## 🧩 技能系统

Autopilot Core 内置 **11 个技能**，覆盖自动化工作流的全流程。

### 技能概览

| 技能 | 目录 | 功能 | 触发场景 |
|------|------|------|---------|
| **skill-selector** | `skills/skill-selector/` | 根据文件类型选择技能 | 每次运行 |
| **auto-trigger** | `skills/auto-trigger/` | 基于变更自动触发技能 | git diff |
| **skill-chain** | `skills/skill-chain/` | 编排技能执行顺序 | 复杂工作流 |
| **parallel-executor** | `skills/parallel-executor/` | 并行执行多个技能 | 高性能执行 |
| **test-runner** | `skills/test-runner/` | 运行测试并报告 | `*.py` 文件 |
| **commit-validator** | `skills/commit-validator/` | 验证提交信息格式 | `*.py`, `*.md` |
| **self-healing-executor** | `skills/self-healing-executor/` | 自动修复常见错误 | 测试失败 |
| **project-health-monitor** | `skills/project-health-monitor/` | 检查项目健康状态 | `server.py` |
| **deployment-checker** | `skills/deployment-checker/` | 验证部署配置 | `*.json` |
| **learning-recorder** | `skills/learning-recorder/` | 记录学习数据 | 所有文件 |
| **notification-hub** | `skills/notification-hub/` | 发送通知 | 执行完成 |

### 技能详细说明

#### 1. skill-selector（技能选择器）

**功能**：根据文件变更类型和内容选择合适的技能组合。

**工作流程**：
```
文件变更 → 模式匹配 → 风险评估 → 生成执行计划
```

**触发规则**：
```python
SKILL_RULES = {
    "*.py": ["test-runner", "commit-validator"],
    "tests/**/*.py": ["test-runner"],
    "server.py": ["project-health-monitor"],
    "ai_self_healing/**": ["self-healing-executor"],
    "*.json": ["deployment-checker"],
    ".claude/skills/**": ["learning-recorder"],
}
```

**使用**：
```bash
python skills/skill-selector/scripts/select_skills.py -f server.py tests/
```

#### 2. test-runner（测试运行器）

**功能**：运行项目测试并收集结果。

**特性**：
- 支持 pytest/unittest
- 并行执行测试
- 失败重试
- 详细错误报告

**使用**：
```bash
python skills/test-runner/scripts/run_tests.py --path tests/
python skills/test-runner/scripts/run_tests.py --path tests/ --parallel
```

#### 3. commit-validator（提交验证器）

**功能**：验证 git 提交信息格式，确保提交信息符合规范。

**格式**：
```
<type>: <short summary>

[optional body]

[optional footer]
```

**type 类型**：
| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: add iOS screen recording` |
| `fix` | Bug 修复 | `fix: resolve tool registry duplication` |
| `refactor` | 重构 | `refactor: optimize async execution` |
| `chore` | 杂项 | `chore: ignore pyc files` |
| `docs` | 文档 | `docs: update README` |
| `test` | 测试 | `test: add coverage for healing` |
| `security` | 安全 | `security: prevent path traversal` |
| `perf` | 性能 | `perf: cache tool instances` |

**使用**：
```bash
python skills/commit-validator/scripts/validate.py
python skills/commit-validator/scripts/validate.py --file CHANGELOG.md
```

#### 4. self-healing-executor（自愈执行器）

**功能**：自动检测和修复常见错误。

**错误分类**：
| 类别 | 错误类型 | 修复策略 |
|------|---------|---------|
| `import_error` | 模块导入失败 | 检查依赖安装 |
| `syntax_error` | 语法错误 | 显示错误位置 |
| `test_failure` | 测试失败 | 分析失败原因 |
| `timeout` | 执行超时 | 优化执行时间 |
| `resource_error` | 资源耗尽 | 清理缓存 |
| `config_error` | 配置错误 | 验证配置项 |
| `permission_error` | 权限问题 | 检查文件权限 |
| `unknown_error` | 未知错误 | 记录并报告 |

**使用**：
```bash
python skills/self-healing-executor/scripts/heal.py
python skills/self-healing-executor/scripts/heal.py --check test_failure
```

#### 5. parallel-executor（并行执行器）

**功能**：并行执行多个技能，最大化利用多核 CPU。

**特性**：
- 可配置并行度（默认 3）
- 阶段依赖管理
- 自适应重试
- 详细结果报告

**使用**：
```bash
python skills/parallel-executor/scripts/run_parallel.py --plan .autopilot/state/.autonomous_plan.json
```

#### 6. notification-hub（通知中心）

**功能**：发送执行结果通知。

**支持渠道**：
| 渠道 | 说明 | 配置 |
|------|------|------|
| `osascript` | macOS 通知 | 系统默认 |
| `Slack` | Slack 消息 | `SLACK_WEBHOOK_URL` |
| `Email` | 邮件通知 | SMTP 配置 |
| `Log` | 文件日志 | 日志文件路径 |

**使用**：
```bash
python skills/notification-hub/scripts/notify.py send -m "部署成功" -l success
```

### 添加自定义技能

在 `.autopilot.yaml` 中添加：

```yaml
skills:
  - name: my-custom-skill
    trigger: "*.py"
    action: "python /path/to/my-skill.py"
    enabled: true
```

或在 CLI 中运行时指定：

```bash
autopilot run -f server.py --extra-skill my-custom-skill
```

---

## ⚙️ 配置系统

### 分层配置

Autopilot 使用 **三层配置**，优先级：**本地 > 项目 > 全局**

```
┌─────────────────────────────────────────────────┐
│  本地配置 (优先级最高)                            │
│  ~/.autopilot/config.yaml                        │
│  - 用户级默认配置                                 │
│  - 不提交到 git                                   │
└─────────────────────────────────────────────────┘
                    ▲
┌─────────────────────────────────────────────────┐
│  项目配置                                         │
│  <project>/.autopilot.yaml                       │
│  - 项目级配置，可提交到 git                       │
│  - 团队共享                                       │
└─────────────────────────────────────────────────┘
                    ▲
┌─────────────────────────────────────────────────┐
│  全局配置 (优先级最低)                           │
│  <project>/.autopilot.local.yaml                 │
│  - 本地机器覆盖                                   │
│  - 不提交到 git                                   │
└─────────────────────────────────────────────────┘
```

### 配置结构

```yaml
# .autopilot.yaml
verbose: false
dry_run: false

learning:
  enabled: true
  min_samples: 3
  db_path: .autopilot/.learning.db

executor:
  max_workers: 3
  timeout: 300
  retry_on_fail: true
  retry_attempts: 2
  backoff_factor: 1.5

monitor:
  debounce_seconds: 10
  max_batch: 30
  check_interval: 5

notification:
  enabled: true
  channels:
    - osascript
  on_success: true
  on_failure: true

auto_heal:
  enabled: true
  max_cycles: 3
  heal_on_failure: true

skills:
  enabled: true
  builtin: true
  custom_path: .autopilot/skills

git_hooks:
  pre_commit: true
  post_commit: true
  pre_push: false
```

### 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `verbose` | bool | `false` | 详细输出 |
| `dry_run` | bool | `false` | 干跑模式，不实际执行 |
| `learning.enabled` | bool | `true` | 启用学习引擎 |
| `learning.min_samples` | int | `3` | 最少样本数才能预测 |
| `learning.db_path` | str | `.autopilot/.learning.db` | 数据库路径 |
| `executor.max_workers` | int | `3` | 最大并行数 |
| `executor.timeout` | int | `300` | 单任务超时（秒） |
| `executor.retry_on_fail` | bool | `true` | 失败自动重试 |
| `executor.retry_attempts` | int | `2` | 最大重试次数 |
| `executor.backoff_factor` | float | `1.5` | 重试退避因子 |
| `monitor.debounce_seconds` | int | `10` | git 变更防抖时间 |
| `monitor.max_batch` | int | `30` | 最大批量处理文件数 |
| `notification.enabled` | bool | `true` | 启用通知 |
| `notification.channels` | list | `["osascript"]` | 通知渠道 |
| `auto_heal.enabled` | bool | `true` | 启用自愈 |
| `auto_heal.max_cycles` | int | `3` | 最大自愈循环次数 |
| `git_hooks.pre_commit` | bool | `true` | pre-commit hook |
| `git_hooks.post_commit` | bool | `true` | post-commit hook |

### 管理配置

```bash
# 查看当前配置
autopilot config show

# 设置配置项
autopilot config set learning.enabled false
autopilot config set executor.max_workers 5

# 重置配置
autopilot config reset

# 保存到本地配置
autopilot config set executor.timeout 600 --local
```

---

## 📊 学习引擎

### 数据库结构

```sql
-- 文件统计（按文件跟踪成功率）
CREATE TABLE file_stats (
    file TEXT PRIMARY KEY,
    success INTEGER DEFAULT 0,
    fail INTEGER DEFAULT 0,
    last_run TEXT
);

-- 技能统计（按技能跟踪成功率）
CREATE TABLE skill_stats (
    skill TEXT PRIMARY KEY,
    success INTEGER DEFAULT 0,
    fail INTEGER DEFAULT 0
);

-- 模式统计（按文件模式跟踪成功率）
CREATE TABLE pattern_stats (
    pattern TEXT PRIMARY KEY,
    success INTEGER DEFAULT 0,
    fail INTEGER DEFAULT 0
);

-- 运行历史（完整执行记录）
CREATE TABLE run_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file TEXT, chain TEXT, skill TEXT,
    success INTEGER, timestamp TEXT
);

-- 文件运行记录（按文件+链条的唯一记录）
CREATE TABLE file_runs (
    file TEXT, chain TEXT, success INTEGER,
    timestamp TEXT,
    PRIMARY KEY (file, chain, timestamp)
);

-- 预测数据（用于时间序列分析）
CREATE TABLE predictions (
    chain TEXT,
    predicted_rate REAL,
    confidence REAL,
    trend_slope REAL,
    risk TEXT,
    generated_at TEXT,
    PRIMARY KEY (chain, generated_at)
);
```

### 预测算法

**1. 移动平均（平滑短期波动）**
```python
recent_avg = sum(rates[-5:]) / 5  # 最近 5 次的平均
```

**2. 加权平均（越近越重要）**
```python
weights = range(1, len(rates) + 1)
weighted_avg = sum(r * w for r, w in zip(rates, weights)) / sum(weights)
```

**3. 线性回归（预测趋势）**
```python
n = len(rates)
x_mean = (n - 1) / 2
y_mean = sum(rates) / n

slope = sum((i - x_mean) * (rates[i] - y_mean) for i in range(n)) / \
        sum((i - x_mean) ** 2 for i in range(n))

predicted_rate = weighted_avg + slope * days_ahead
```

**4. 置信度计算**
```python
# 一致性（斜率越小越一致）
consistency = 1.0 - min(1.0, abs(slope) * 10)

# 样本置信度（14天数据为满分）
sample_confidence = min(1.0, n / 14)

# 综合置信度
confidence = (consistency + sample_confidence) / 2
```

### 风险等级

| 预测成功率 | 风险等级 | 建议 |
|-----------|---------|------|
| < 30% | 🔴 高 | 考虑使用更安全的执行方案 |
| 30% - 50% | 🟡 中 | 启用 self-healing 备选方案 |
| > 50% | 🟢 低 | 可以正常执行 |

### 使用预测

```bash
# 预测单个链条
autopilot predict --chain full-auto

# 生成预测报告
autopilot predict --report

# 查看详细 JSON
autopilot predict --chain full-auto --json
```

---

## 🔧 CLI 命令

### 命令总览

| 命令 | 说明 | 示例 |
|------|------|------|
| `autopilot init` | 初始化项目 | `autopilot init` |
| `autopilot status` | 查看状态 | `autopilot status` |
| `autopilot run` | 运行自动驾驶 | `autopilot run -f file.py` |
| `autopilot dashboard` | 监控面板 | `autopilot dashboard` |
| `autopilot predict` | 预测分析 | `autopilot predict --report` |
| `autopilot health` | 健康检查 | `autopilot health` |
| `autopilot heal` | 闭环自愈 | `autopilot heal` |
| `autopilot config` | 配置管理 | `autopilot config show` |
| `autopilot daemon` | 持续监控 | `autopilot daemon` |
| `autopilot scheduler` | 定时任务 | `autopilot scheduler --list` |
| `autopilot git-hooks` | Git Hooks | `autopilot git-hooks --install` |
| `autopilot nlp` | 自然语言 | `autopilot nlp run tests` |

### 详细用法

#### `autopilot run`

```bash
# 基本运行（处理 git 变更）
autopilot run

# 指定文件
autopilot run -f server.py tests/

# 干跑模式（不实际执行）
autopilot run --dry-run

# 连续监控模式
autopilot run --continuous --interval 60

# 最大循环次数
autopilot run --continuous --max-cycles 10
```

#### `autopilot dashboard`

```bash
# 查看监控面板
autopilot dashboard

# JSON 输出
autopilot dashboard --json

# 自动刷新（每 30 秒）
autopilot dashboard --refresh 30
```

#### `autopilot health`

```bash
# 健康检查
autopilot health
```

输出示例：
```
🏥============================================================
   Autopilot 健康检查
============================================================

   整体状态: ✅ 健康
   过去24小时失败: 0次

   关键检查:
     ✅ 数据库连接
     ✅ 技能目录存在
     ✅ 配置文件有效
     ✅ Git 仓库正常
```

#### `autopilot config`

```bash
# 显示所有配置
autopilot config show

# 设置配置项
autopilot config set learning.enabled false
autopilot config set executor.max_workers 5

# 本地配置（不提交）
autopilot config set notification.channels '["slack"]' --local

# 重置配置
autopilot config reset
```

#### `autopilot git-hooks`

```bash
# 查看安装状态
autopilot git-hooks --list

# 安装 hooks
autopilot git-hooks --install

# 卸载 hooks
autopilot git-hooks --uninstall
```

#### `autopilot daemon`

```bash
# 启动守护进程（监控 git 变更）
autopilot daemon

# 自定义配置
autopilot daemon --debounce 5 --interval 10 --max-batch 50
```

#### `autopilot scheduler`

```bash
# 列出定时任务
autopilot scheduler --list

# 运行待执行任务
autopilot scheduler --run

# 生成报告
autopilot scheduler --report --days 7
```

---

## 🔗 协同外部 CLI

Autopilot Core 不仅可以运行内置自动驾驶，还支持与外部独立 CLI 协同工作，将它们纳入统一的执行和记录体系。

### 定位说明

**Autopilot Core 负责**：
- 执行
- 触发
- 编排
- 记录
- 持续化运行

**Autopilot Core 不负责**：
- 审核决策
- findings 语义理解
- 报告质量判断
- 领域化治理逻辑

**外部 CLI 是平级协作者**，如：
- 审核 CLI
- 安全扫描 CLI
- 合规检查 CLI
- 发布检查 CLI

### 外部工作流配置

在 `.autopilot.yaml` 中配置外部工作流：

```yaml
workflows:
  - name: pre-pr
    description: Run local automation and external governance checks
    steps:
      - name: local-autopilot
        command: autopilot run
        timeout: 300
      - name: governance-check
        command: some-governance-cli run --path .
        timeout: 600

  - name: security-scan
    description: Run security scans
    steps:
      - name: secrets-scan
        command: scan --type secrets
        timeout: 120
      - name: vulnerability-scan
        command: scan --type vulns
        timeout: 300
        continue_on_error: true  # 允许继续执行后续步骤
```

**步骤配置说明**：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `name` | string | 必需 | 步骤名称 |
| `command` | string | 必需 | 要执行的命令 |
| `timeout` | int | 300 | 超时时间（秒） |
| `cwd` | string | 继承 | 工作目录 |
| `continue_on_error` | bool | false | 失败时是否继续 |
| `env` | dict | null | 环境变量 |

### Workflow 命令

#### 列出工作流

```bash
autopilot workflow list
```

输出示例：
```
============================================================
📋 已配置的工作流 (2)
============================================================

📦 pre-pr
   描述: Run local automation and external governance checks
   步骤数: 2
   - local-autopilot: autopilot run
   - governance-check: some-governance-cli run --path .

📦 security-scan
   描述: Run security scans
   步骤数: 2
   - secrets-scan: scan --type secrets
   - vulnerability-scan: scan --type vulns

============================================================
```

#### 显示工作流详情

```bash
autopilot workflow show <name>
```

示例：
```bash
autopilot workflow show pre-pr
```

输出：
```
============================================================
📦 工作流: pre-pr
============================================================
📝 描述: Run local automation and external governance checks

📊 步骤 (2):

  步骤 1: local-autopilot
    命令: autopilot run
    超时: 300s
    工作目录: (继承)
    失败继续: 否

  步骤 2: governance-check
    命令: some-governance-cli run --path .
    超时: 600s
    工作目录: (继承)
    失败继续: 否

============================================================
```

#### 运行工作流

```bash
autopilot workflow run <name>
```

示例：
```bash
autopilot workflow run pre-pr
```

#### 查看工作流历史

```bash
autopilot workflow history <name>
autopilot workflow history <name> --limit 5
```

示例：
```bash
autopilot workflow history pre-pr
```

输出：
```
============================================================
📋 工作流 'pre-pr' 执行历史 (最近 3 条)
============================================================

✅ run_id: a1b2c3d4
   开始时间: 2026-05-12T10:00:00
   耗时: 125.50s
   退出码: 0

❌ run_id: e5f6g7h8
   开始时间: 2026-05-12T09:30:00
   耗时: 60.23s
   退出码: 1
   失败步骤: governance-check

============================================================
```

#### 校验工作流配置

```bash
autopilot workflow validate
```

示例：
```bash
# 校验成功
$ autopilot workflow validate
✅ 配置校验通过
   工作流数量: 2

# 校验失败
$ autopilot workflow validate
❌ 配置校验失败，发现 2 个问题:
   - workflow 'bad-workflow': step 0: step missing 'command'
   - workflow 'bad-workflow': step 1: 'timeout' must be a positive integer
```

### --json 输出

多个命令支持 `--json` 参数，便于脚本消费：

```bash
# workflow list --json
autopilot workflow list --json

# workflow show --json
autopilot workflow show <name> --json

# workflow run --json
autopilot workflow run <name> --json

# workflow history --json
autopilot workflow history <name> --json

# exec --json
autopilot exec --json -- echo "hello"
```

JSON 输出特点：
- 纯 JSON，无人类可读文字混入
- 字段稳定，适合程序解析
- 退出码语义不变（0=成功，非0=失败）

### Exec 命令

执行任意外部命令并统一记录结果：

```bash
autopilot exec -- <command...>
```

**示例**：

```bash
# 执行单个命令
autopilot exec -- echo "Hello"

# 执行带参数的命令
autopilot exec -- some-cli check --target .

# 执行并指定超时
autopilot exec -t 120 -- long-running-command

# 执行并指定工作目录
autopilot exec -p /path/to/project -- command
```

### 真实项目协同示例

假设项目使用 `revieworg` CLI 进行代码审核：

```yaml
# .autopilot.yaml
workflows:
  - name: pre-merge
    description: Pre-merge checks including external review
    steps:
      - name: run-tests
        command: pytest tests/
        timeout: 300
      - name: run-lint
        command: ruff check .
        timeout: 60
      - name: external-review
        command: revieworg decide --path . --goal pre-merge
        timeout: 600
        continue_on_error: true
```

执行：
```bash
# 运行完整 pre-merge 检查
autopilot workflow run pre-merge

# 或者直接执行审核命令
autopilot exec -- revieworg decide --path . --goal pre-merge
```

### 执行结果落盘

所有执行结果都会自动落盘到 `.autopilot/state/` 目录：

```
.autopilot/
├── state/
│   ├── workflows/
│   │   └── pre-pr/
│   │       └── a1b2c3d4.json   # workflow 执行结果
│   └── exec/
│       └── e5f6g7h8.json        # exec 执行结果
```

**Workflow 结果结构**：

```json
{
  "run_id": "a1b2c3d4",
  "workflow_name": "pre-pr",
  "command": "workflow: pre-pr",
  "cwd": "/path/to/project",
  "started_at": "2026-05-12T10:00:00",
  "duration_seconds": 125.5,
  "exit_code": 0,
  "success": true,
  "steps": [
    {
      "step_name": "local-autopilot",
      "command": "autopilot run",
      "duration_seconds": 45.2,
      "exit_code": 0,
      "success": true,
      "stdout_summary": "...",
      "stderr_summary": ""
    }
  ],
  "failed_step": null,
  "completed_steps": ["local-autopilot", "governance-check"]
}
```

### 与 Git Hooks 集成

在 `.autopilot.yaml` 中配置 hooks 触发 workflow：

```yaml
git_hooks:
  pre_commit: true
  post_commit: true
  pre_push: false

# 关联的 workflow
workflows:
  - name: commit-check
    steps:
      - name: lint
        command: ruff check .
      - name: test
        command: pytest
```

---

## 🧪 开发指南

### 开发环境

```bash
# 克隆仓库
git clone https://github.com/packs/autopilot-core.git
cd autopilot-core

# 安装（开发模式）
pip install -e ".[dev]"

# 运行测试
pytest

# 代码格式
ruff format .
ruff check .
```

### 添加新技能

**1. 创建技能目录结构**

```
skills/
└── my-skill/
    ├── SKILL.md
    └── scripts/
        └── run.py
```

**2. 编写 SKILL.md**

```markdown
# My Skill

## 功能
描述技能功能

## 触发规则
- `*.py`: 主要触发
- `*.json`: 可选触发

## 使用方式
```bash
python skills/my-skill/scripts/run.py --arg value
```
```

**3. 编写脚本**

```python
#!/usr/bin/env python3
"""My Skill"""

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="My Skill")
    parser.add_argument("--file", "-f", help="目标文件")
    args = parser.parse_args()

    # 实现技能逻辑
    print("Running my skill...")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
```

### 扩展学习引擎

```python
from autopilot_core.core.learning_engine import LearningEngine

class CustomLearningEngine(LearningEngine):
    def custom_prediction(self, files, context):
        """自定义预测逻辑"""
        # 分析文件历史
        # 生成预测
        return {
            "predicted_rate": 0.85,
            "confidence": 0.7,
            "risk": "low"
        }

# 使用自定义引擎
engine = CustomLearningEngine(db_path=".autopilot/.learning.db")
result = engine.predict_for_files(["server.py"])
```

### API 集成

```python
from autopilot_core.core.autonomous import AutonomousScheduler, AutopilotConfig

# 创建调度器
config = AutopilotConfig(
    project_root=Path("/path/to/project"),
    learning_enabled=True,
    max_workers=3
)
scheduler = AutonomousScheduler(config=config)

# 运行完整周期
success = scheduler.run_full_cycle(files=["server.py", "tests/"])

# 获取结果
print(scheduler.results)
```

---

## ❓ FAQ

### Q: 如何卸载？

```bash
pip uninstall autopilot-core
rm -rf ~/.autopilot  # 可选，删除全局配置
```

### Q: 如何禁用学习引擎？

```bash
autopilot config set learning.enabled false
```

### Q: 如何添加自定义通知渠道？

在 `.autopilot.yaml` 中配置：

```yaml
notification:
  channels:
    - osascript
    - slack

slack:
  webhook_url: https://hooks.slack.com/...
```

### Q: 如何查看详细的执行日志？

```bash
# 干跑模式查看完整计划
autopilot run --dry-run -f server.py

# 查看状态
autopilot status
```

### Q: 如何贡献代码？

1. Fork 仓库
2. 创建分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### Q: 支持哪些 Python 版本？

- Python 3.8+
- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12

### Q: 支持哪些操作系统？

- Linux（测试通过）
- macOS（测试通过）
- Windows（WSL 兼容）

---

## 📦 发行说明

### 适合什么项目

**Autopilot Core** 适合以下类型的项目：

| 项目类型 | 说明 |
|---------|------|
| **需要 CI/CD 自动化** | 自动触发测试、lint、部署检查 |
| **有多步骤工作流** | 需要顺序执行多个外部 CLI |
| **需要统一记录** | 想把执行结果统一落盘便于审计 |
| **使用外部治理工具** | 已有审核CLI/安全扫描CLI，想统一编排 |
| **AI Agent 集成** | 需要为 Claude Code 等 AI Agent 提供自动化执行能力 |

**不适合**：
- 需要复杂 DAG 或条件分支的工作流（V2 预留）
- 需要审核决策逻辑的项目（autopilot-core 只负责执行，不做决策）
- 依赖特定工具输出的结构化解析

### 版本说明

| 版本 | 状态 | 说明 |
|------|------|------|
| V1.0 | ✅ 稳定 | 核心功能：workflow、exec、validate |
| V1.1 | ✅ 当前 | 增加 history、--json、测试补齐 |
| V2.0 | 规划中 | 条件执行、变量传递、Dashboard 集成 |

---

## ⚠️ 已知限制

1. **Workflow 只支持顺序执行** - 不支持并行或 DAG
2. **不支持变量传递** - 步骤之间无法共享状态
3. **不支持条件分支** - 根据上一步结果决定下一步（V2 规划）
4. **测试偏单元级别** - 暂无端到端集成测试
5. **仅支持 Python 3.8+** - 不支持 Python 3.7

---

## 📝 License

MIT License - 详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- [Claude Code](https://claude.ai/code) - AI 编程助手
- [MCP Protocol](https://modelcontextprotocol.io) - 模型上下文协议

---

<p align="center">
  <strong>Autopilot Core</strong> — 让自动化更智能
</p>