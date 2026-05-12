# Autopilot Core

> 🤖 General Autonomous Driving Mode — Give any project intelligent scheduling + learning prediction + closed-loop self-healing capabilities

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/packs/autopilot-core?style=social)](https://github.com/packs/autopilot-core)

**Autopilot Core** is a general-purpose intelligent scheduling system based on Claude Code, encapsulating complex automation workflows into simple CLI commands. With just `autopilot run`, the system automatically handles: skill selection → execution planning → verification → recording → notification.

---

## Table of Contents

- [✨ Features](#-features)
- [🚀 Quick Start](#-quick-start)
- [📖 Detailed Guide](#-detailed-guide)
- [🧩 Skill System](#-skill-system)
- [⚙️ Config System](#-config-system)
- [📊 Learning Engine](#-learning-engine)
- [🔧 CLI Commands](#-cli-commands)
- [🔗 External CLI Integration](#-external-cli-integration)
- [🧪 Development Guide](#-development-guide)
- [❓ FAQ](#-faq)
- [📦 Release Notes](#-release-notes)
- [⚠️ Known Limitations](#-known-limitations)

---

## ✨ Features

### Core Capabilities

| Feature | Description |
|---------|-------------|
| **🎯 Intelligent Scheduling** | 5-step closed loop: skill selection → execution planning → verification → learning recording → notification |
| **📈 Self-Learning Engine** | SQLite persistence + time series prediction — gets smarter with use |
| **🔄 Closed-Loop Self-Healing** | Auto-detect, classify, fix, verify failures |
| **⚙️ Layered Config** | Global/project/local three-layer override, works out of the box |
| **🧩 11 Built-in Skills** | Covers testing, verification, fixing, monitoring, notification full流程 |
| **🌐 MCP Protocol** | Native MCP Server support, can connect to AI Agents |
| **⚡ High Performance** | Parallel execution + adaptive retry + intelligent timeout |
| **🔌 Zero-Dependency Core** | Core requires only Python 3.8+, no heavy dependencies |

### Use Cases

- 🏭 **CI/CD Integration** — Auto-trigger testing/verification/deployment on code commits
- 🔍 **Code Review Automation** — Auto-check code quality on every commit
- 🐛 **Self-Healing** — Auto-fix common test failures and build errors
- 📊 **Project Health Monitoring** — Continuously track codebase health status
- 🤖 **MCP Agent Empowerment** — Provide autonomous execution capability for AI Agents

---

## 🚀 Quick Start

### Installation

#### Method 1: pip install (Recommended)

```bash
pip install autopilot-core
```

#### Method 2: Source Install

```bash
git clone https://github.com/packs/autopilot-core.git
cd autopilot-core
pip install -e .
```

#### Method 3: Homebrew (macOS)

```bash
brew install autopilot-core
```

### Initialize Project

```bash
# Enter target project
cd /path/to/your-project

# Initialize autopilot config
autopilot init
```

`autopilot init` creates the following structure:

```
your-project/
├── .autopilot.yaml          # Project config (can be committed to git)
├── .autopilot/              # Runtime directory
│   ├── skills/              # Skills directory (11 built-in skills)
│   ├── state/               # State files, execution plans
│   └── .learning.db         # Learning database
└── .gitignore               # Auto-adds .autopilot/ to .gitignore
```

### First Run

```bash
# View status
autopilot status

# Run autonomous driving (process all git changed files)
autopilot run

# Run with specified files
autopilot run -f server.py tests/

# View monitoring dashboard
autopilot dashboard
```

---

## 📖 Detailed Guide

### How It Works

The core of Autopilot Core is a **5-step closed-loop execution framework**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Autonomous Scheduling Center                 │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │ Step 1   │───▶│ Step 2   │───▶│ Step 3   │───▶│ Step 4   │  │
│  │  Skill   │    │ Execution│    │ Verify   │    │  Record  │  │
│  │Selection │    │  Plan    │    │ Results  │    │  Learn   │  │
│  │          │    │          │    │          │    │          │  │
│  │ • File   │    │ • Parallel│   │ • Syntax │    │ • Pattern│  │
│  │   Type   │    │  Execute │    │  Check  │    │  Analysis│  │
│  │ • Risk   │    │ • Retry  │    │ • Business│   │ • Predict│  │
│  │  Assess  │    │ • Timeout│    │  Verify  │    │  Update  │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│        │              │              │              │            │
│        └──────────────┴──────────────┴──────────────┘            │
│                            │                                    │
│                     ┌──────┴──────┐                             │
│                     │   Step 5    │                             │
│                     │Send Notice  │                             │
│                     └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Layer                              │
│                    CLI / MCP Server                             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                       Scheduler (autonomous.py)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ SkillRegistry│  │PlanGenerator│  │   ClosedLoopHealer    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                       Skills Layer (skills/)                    │
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
│                  Learning Layer (learning_engine.py)             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  SQLite DB   │  │ Prediction   │  │   Trend Analysis    │   │
│  │  Persistent  │  │ Time Series  │  │   Risk Assessment   │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure

```
autopilot_core/
├── cli.py                          # 🎯 CLI entry point (all commands)
├── __init__.py
│
├── core/                           # Core modules
│   ├── __init__.py
│   ├── autonomous.py               # 🚗 Autonomous scheduling center
│   ├── learning_engine.py          # 📈 Learning engine + prediction
│   ├── config.py                  # ⚙️ Layered config system
│   ├── auto_heal.py               # 🔄 Closed-loop self-healing
│   ├── dashboard.py               # 📊 Monitoring dashboard
│   ├── daemon.py                  # 🕐️ Continuous monitoring daemon
│   ├── scheduler.py               # ⏰ Scheduled task scheduler
│   ├── git_hooks.py               # 🪝 Git Hooks integration
│   └── nlp.py                     # 💬 Natural language interface
│
├── skills/                         # 🧩 Built-in skill packages
│   ├── skill-selector/             # 📋 Skill selector
│   ├── auto-trigger/              # ⚡ Auto trigger
│   ├── skill-chain/                # 🔗 Skill chain orchestration
│   ├── parallel-executor/          # ⚡ Parallel executor
│   ├── test-runner/               # 🧪 Test runner
│   ├── commit-validator/          # ✅ Commit validator
│   ├── self-healing-executor/      # 🔧 Self-healing executor
│   ├── project-health-monitor/     # 🏥 Project health monitor
│   ├── deployment-checker/         # 🚀 Deployment checker
│   ├── learning-recorder/          # 📝 Learning recorder
│   └── notification-hub/           # 📱 Notification center
│
└── mcp/                            # 🌐 MCP Server
    └── server.py                  # MCP protocol adapter layer
```

---

## 🧩 Skill System

Autopilot Core has **11 built-in skills** covering the full automation workflow.

### Skills Overview

| Skill | Directory | Function | Trigger Scenario |
|-------|-----------|----------|-------------------|
| **skill-selector** | `skills/skill-selector/` | Select skills based on file type | Every run |
| **auto-trigger** | `skills/auto-trigger/` | Auto-trigger skills based on changes | git diff |
| **skill-chain** | `skills/skill-chain/` | Orchestrate skill execution order | Complex workflows |
| **parallel-executor** | `skills/parallel-executor/` | Execute multiple skills in parallel | High-performance execution |
| **test-runner** | `skills/test-runner/` | Run tests and report | `*.py` files |
| **commit-validator** | `skills/commit-validator/` | Validate commit message format | `*.py`, `*.md` |
| **self-healing-executor** | `skills/self-healing-executor/` | Auto-fix common errors | Test failures |
| **project-health-monitor** | `skills/project-health-monitor/` | Check project health | `server.py` |
| **deployment-checker** | `skills/deployment-checker/` | Validate deployment config | `*.json` |
| **learning-recorder** | `skills/learning-recorder/` | Record learning data | All files |
| **notification-hub** | `skills/notification-hub/` | Send notifications | Execution complete |

### Skill Details

#### 1. skill-selector

**Function**: Select appropriate skill combinations based on file change types and content.

**Workflow**:
```
File Change → Pattern Matching → Risk Assessment → Generate Execution Plan
```

**Trigger Rules**:
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

**Usage**:
```bash
python skills/skill-selector/scripts/select_skills.py -f server.py tests/
```

#### 2. test-runner

**Function**: Run project tests and collect results.

**Features**:
- Support pytest/unittest
- Parallel test execution
- Failure retry
- Detailed error reporting

**Usage**:
```bash
python skills/test-runner/scripts/run_tests.py --path tests/
python skills/test-runner/scripts/run_tests.py --path tests/ --parallel
```

#### 3. commit-validator

**Function**: Validate git commit message format to ensure commits follow conventions.

**Format**:
```
<type>: <short summary>

[optional body]

[optional footer]
```

**Type List**:
| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat: add iOS screen recording` |
| `fix` | Bug fix | `fix: resolve tool registry duplication` |
| `refactor` | Refactoring | `refactor: optimize async execution` |
| `chore` | Chores | `chore: ignore pyc files` |
| `docs` | Documentation | `docs: update README` |
| `test` | Tests | `test: add coverage for healing` |
| `security` | Security | `security: prevent path traversal` |
| `perf` | Performance | `perf: cache tool instances` |

**Usage**:
```bash
python skills/commit-validator/scripts/validate.py
python skills/commit-validator/scripts/validate.py --file CHANGELOG.md
```

#### 4. self-healing-executor

**Function**: Auto-detect and fix common errors.

**Error Classification**:
| Category | Error Type | Fix Strategy |
|----------|------------|--------------|
| `import_error` | Module import failed | Check dependency installation |
| `syntax_error` | Syntax error | Show error location |
| `test_failure` | Test failure | Analyze failure cause |
| `timeout` | Execution timeout | Optimize execution time |
| `resource_error` | Resource exhausted | Clean cache |
| `config_error` | Config error | Validate config items |
| `permission_error` | Permission issue | Check file permissions |
| `unknown_error` | Unknown error | Record and report |

**Usage**:
```bash
python skills/self-healing-executor/scripts/heal.py
python skills/self-healing-executor/scripts/heal.py --check test_failure
```

#### 5. parallel-executor

**Function**: Execute multiple skills in parallel to maximize multi-core CPU utilization.

**Features**:
- Configurable parallelism (default 3)
- Stage dependency management
- Adaptive retry
- Detailed result reporting

**Usage**:
```bash
python skills/parallel-executor/scripts/run_parallel.py --plan .autopilot/state/.autonomous_plan.json
```

#### 6. notification-hub

**Function**: Send execution result notifications.

**Supported Channels**:
| Channel | Description | Config |
|---------|-------------|--------|
| `osascript` | macOS notification | System default |
| `Slack` | Slack message | `SLACK_WEBHOOK_URL` |
| `Email` | Email notification | SMTP config |
| `Log` | File log | Log file path |

**Usage**:
```bash
python skills/notification-hub/scripts/notify.py send -m "Deployment successful" -l success
```

### Adding Custom Skills

Add in `.autopilot.yaml`:

```yaml
skills:
  - name: my-custom-skill
    trigger: "*.py"
    action: "python /path/to/my-skill.py"
    enabled: true
```

Or specify at CLI runtime:

```bash
autopilot run -f server.py --extra-skill my-custom-skill
```

---

## ⚙️ Config System

### Layered Config

Autopilot uses **three-layer config** with priority: **Local > Project > Global**

```
┌─────────────────────────────────────────────────┐
│  Local Config (Highest Priority)                │
│  ~/.autopilot/config.yaml                        │
│  - User-level defaults                          │
│  - Not committed to git                        │
└─────────────────────────────────────────────────┘
                    ▲
┌─────────────────────────────────────────────────┐
│  Project Config                                 │
│  <project>/.autopilot.yaml                      │
│  - Project-level config, can be committed       │
│  - Shared across team                          │
└─────────────────────────────────────────────────┘
                    ▲
┌─────────────────────────────────────────────────┐
│  Global Config (Lowest Priority)                │
│  <project>/.autopilot.local.yaml                │
│  - Local machine override                       │
│  - Not committed to git                        │
└─────────────────────────────────────────────────┘
```

### Config Structure

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

### Config Options

| Config Item | Type | Default | Description |
|-------------|------|---------|-------------|
| `verbose` | bool | `false` | Verbose output |
| `dry_run` | bool | `false` | Dry run mode, no actual execution |
| `learning.enabled` | bool | `true` | Enable learning engine |
| `learning.min_samples` | int | `3` | Min samples for prediction |
| `learning.db_path` | str | `.autopilot/.learning.db` | Database path |
| `executor.max_workers` | int | `3` | Max parallelism |
| `executor.timeout` | int | `300` | Single task timeout (seconds) |
| `executor.retry_on_fail` | bool | `true` | Auto retry on failure |
| `executor.retry_attempts` | int | `2` | Max retry attempts |
| `executor.backoff_factor` | float | `1.5` | Retry backoff factor |
| `monitor.debounce_seconds` | int | `10` | Git change debounce time |
| `monitor.max_batch` | int | `30` | Max batch processing files |
| `notification.enabled` | bool | `true` | Enable notification |
| `notification.channels` | list | `["osascript"]` | Notification channels |
| `auto_heal.enabled` | bool | `true` | Enable self-healing |
| `auto_heal.max_cycles` | int | `3` | Max self-healing cycles |
| `git_hooks.pre_commit` | bool | `true` | pre-commit hook |
| `git_hooks.post_commit` | bool | `true` | post-commit hook |

### Managing Config

```bash
# View current config
autopilot config show

# Set config item
autopilot config set learning.enabled false
autopilot config set executor.max_workers 5

# Reset config
autopilot config reset

# Save to local config
autopilot config set executor.timeout 600 --local
```

---

## 📊 Learning Engine

### Database Schema

```sql
-- File stats (track success rate by file)
CREATE TABLE file_stats (
    file TEXT PRIMARY KEY,
    success INTEGER DEFAULT 0,
    fail INTEGER DEFAULT 0,
    last_run TEXT
);

-- Skill stats (track success rate by skill)
CREATE TABLE skill_stats (
    skill TEXT PRIMARY KEY,
    success INTEGER DEFAULT 0,
    fail INTEGER DEFAULT 0
);

-- Pattern stats (track success rate by file pattern)
CREATE TABLE pattern_stats (
    pattern TEXT PRIMARY KEY,
    success INTEGER DEFAULT 0,
    fail INTEGER DEFAULT 0
);

-- Run history (complete execution records)
CREATE TABLE run_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file TEXT, chain TEXT, skill TEXT,
    success INTEGER, timestamp TEXT
);

-- File runs (unique records by file+chain)
CREATE TABLE file_runs (
    file TEXT, chain TEXT, success INTEGER,
    timestamp TEXT,
    PRIMARY KEY (file, chain, timestamp)
);

-- Predictions (for time series analysis)
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

### Prediction Algorithm

**1. Moving Average (smooth short-term fluctuations)**
```python
recent_avg = sum(rates[-5:]) / 5  # Average of last 5
```

**2. Weighted Average (more recent = more important)**
```python
weights = range(1, len(rates) + 1)
weighted_avg = sum(r * w for r, w in zip(rates, weights)) / sum(weights)
```

**3. Linear Regression (predict trend)**
```python
n = len(rates)
x_mean = (n - 1) / 2
y_mean = sum(rates) / n

slope = sum((i - x_mean) * (rates[i] - y_mean) for i in range(n)) / \
        sum((i - x_mean) ** 2 for i in range(n))

predicted_rate = weighted_avg + slope * days_ahead
```

**4. Confidence Calculation**
```python
# Consistency (smaller slope = more consistent)
consistency = 1.0 - min(1.0, abs(slope) * 10)

# Sample confidence (14 days of data = full score)
sample_confidence = min(1.0, n / 14)

# Combined confidence
confidence = (consistency + sample_confidence) / 2
```

### Risk Levels

| Predicted Success Rate | Risk Level | Recommendation |
|------------------------|------------|-----------------|
| < 30% | 🔴 High | Consider using safer execution plan |
| 30% - 50% | 🟡 Medium | Enable self-healing backup |
| > 50% | 🟢 Low | Can execute normally |

### Using Predictions

```bash
# Predict single chain
autopilot predict --chain full-auto

# Generate prediction report
autopilot predict --report

# View detailed JSON
autopilot predict --chain full-auto --json
```

---

## 🔧 CLI Commands

### Command Overview

| Command | Description | Example |
|---------|-------------|---------|
| `autopilot init` | Initialize project | `autopilot init` |
| `autopilot status` | View status | `autopilot status` |
| `autopilot run` | Run autonomous driving | `autopilot run -f file.py` |
| `autopilot dashboard` | Monitoring dashboard | `autopilot dashboard` |
| `autopilot predict` | Prediction analysis | `autopilot predict --report` |
| `autopilot health` | Health check | `autopilot health` |
| `autopilot heal` | Closed-loop self-healing | `autopilot heal` |
| `autopilot config` | Config management | `autopilot config show` |
| `autopilot daemon` | Continuous monitoring | `autopilot daemon` |
| `autopilot scheduler` | Scheduled tasks | `autopilot scheduler --list` |
| `autopilot git-hooks` | Git Hooks | `autopilot git-hooks --install` |
| `autopilot nlp` | Natural language | `autopilot nlp run tests` |

### Detailed Usage

#### `autopilot run`

```bash
# Basic run (process git changes)
autopilot run

# Specify files
autopilot run -f server.py tests/

# Dry run mode (no actual execution)
autopilot run --dry-run

# Continuous monitoring mode
autopilot run --continuous --interval 60

# Max cycles
autopilot run --continuous --max-cycles 10
```

#### `autopilot dashboard`

```bash
# View monitoring dashboard
autopilot dashboard

# JSON output
autopilot dashboard --json

# Auto-refresh (every 30 seconds)
autopilot dashboard --refresh 30
```

#### `autopilot health`

```bash
# Health check
autopilot health
```

Sample output:
```
🏥============================================================
   Autopilot Health Check
============================================================

   Overall Status: ✅ Healthy
   Failures in past 24h: 0

   Key Checks:
     ✅ Database connection
     ✅ Skills directory exists
     ✅ Config file valid
     ✅ Git repository normal
```

#### `autopilot config`

```bash
# Show all config
autopilot config show

# Set config item
autopilot config set learning.enabled false
autopilot config set executor.max_workers 5

# Local config (not committed)
autopilot config set notification.channels '["slack"]' --local

# Reset config
autopilot config reset
```

#### `autopilot git-hooks`

```bash
# View installation status
autopilot git-hooks --list

# Install hooks
autopilot git-hooks --install

# Uninstall hooks
autopilot git-hooks --uninstall
```

#### `autopilot daemon`

```bash
# Start daemon (monitor git changes)
autopilot daemon

# Custom config
autopilot daemon --debounce 5 --interval 10 --max-batch 50
```

#### `autopilot scheduler`

```bash
# List scheduled tasks
autopilot scheduler --list

# Run pending tasks
autopilot scheduler --run

# Generate report
autopilot scheduler --report --days 7
```

---

## 🔗 External CLI Integration

Autopilot Core not only runs built-in autonomous driving, but also supports collaborating with external independent CLIs, bringing them into a unified execution and recording system.

### Positioning

**Autopilot Core is responsible for**:
- Execution
- Triggering
- Orchestration
- Recording
- Persistent operation

**Autopilot Core is NOT responsible for**:
- Review decisions
- Finding semantic understanding
- Report quality judgment
- Domain governance logic

**External CLIs are peer collaborators**, such as:
- Review CLIs
- Security scan CLIs
- Compliance check CLIs
- Release check CLIs

### External Workflow Config

Configure external workflows in `.autopilot.yaml`:

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
        continue_on_error: true  # Allow continuing on failure
```

**Step Config Explanation**:

| Config Item | Type | Default | Description |
|-------------|------|---------|-------------|
| `name` | string | Required | Step name |
| `command` | string | Required | Command to execute |
| `timeout` | int | 300 | Timeout (seconds) |
| `cwd` | string | inherit | Working directory |
| `continue_on_error` | bool | false | Continue on failure |
| `env` | dict | null | Environment variables |

### Workflow Commands

#### List Workflows

```bash
autopilot workflow list
```

Sample output:
```
============================================================
📋 Configured Workflows (2)
============================================================

📦 pre-pr
   Description: Run local automation and external governance checks
   Steps: 2
   - local-autopilot: autopilot run
   - governance-check: some-governance-cli run --path .

📦 security-scan
   Description: Run security scans
   Steps: 2
   - secrets-scan: scan --type secrets
   - vulnerability-scan: scan --type vulns

============================================================
```

#### Show Workflow Details

```bash
autopilot workflow show <name>
```

Example:
```bash
autopilot workflow show pre-pr
```

Output:
```
============================================================
📦 Workflow: pre-pr
============================================================
📝 Description: Run local automation and external governance checks

📊 Steps (2):

  Step 1: local-autopilot
    Command: autopilot run
    Timeout: 300s
    Working Dir: (inherit)
    Continue on Error: No

  Step 2: governance-check
    Command: some-governance-cli run --path .
    Timeout: 600s
    Working Dir: (inherit)
    Continue on Error: No

============================================================
```

#### Run Workflow

```bash
autopilot workflow run <name>
```

Example:
```bash
autopilot workflow run pre-pr
```

#### View Workflow History

```bash
autopilot workflow history <name>
autopilot workflow history <name> --limit 5
```

Example:
```bash
autopilot workflow history pre-pr
```

Output:
```
============================================================
📋 Workflow 'pre-pr' Execution History (3 recent)
============================================================

✅ run_id: a1b2c3d4
   Started: 2026-05-12T10:00:00
   Duration: 125.50s
   Exit Code: 0

❌ run_id: e5f6g7h8
   Started: 2026-05-12T09:30:00
   Duration: 60.23s
   Exit Code: 1
   Failed Step: governance-check

============================================================
```

#### Validate Workflow Config

```bash
autopilot workflow validate
```

Example:
```bash
# Validation success
$ autopilot workflow validate
✅ Config validation passed
   Workflow count: 2

# Validation failed
$ autopilot workflow validate
❌ Config validation failed, found 2 issues:
   - workflow 'bad-workflow': step 0: step missing 'command'
   - workflow 'bad-workflow': step 1: 'timeout' must be a positive integer
```

### --json Output

Multiple commands support `--json` for script consumption:

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

JSON output features:
- Pure JSON, no human-readable text mixed in
- Stable fields, suitable for program parsing
- Exit code semantics unchanged (0=success, non-0=failure)

### Exec Command

Execute any external command with unified recording:

```bash
autopilot exec -- <command...>
```

**Examples**:

```bash
# Execute single command
autopilot exec -- echo "Hello"

# Execute command with arguments
autopilot exec -- some-cli check --target .

# Execute with timeout
autopilot exec -t 120 -- long-running-command

# Execute with working directory
autopilot exec -p /path/to/project -- command
```

### Real Project Collaboration Example

Assume project uses `revieworg` CLI for code review:

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

Execute:
```bash
# Run complete pre-merge checks
autopilot workflow run pre-merge

# Or directly execute review command
autopilot exec -- revieworg decide --path . --goal pre-merge
```

### Execution Result Persistence

All execution results automatically persist to `.autopilot/state/` directory:

```
.autopilot/
├── state/
│   ├── workflows/
│   │   └── pre-pr/
│   │       └── a1b2c3d4.json   # Workflow execution result
│   └── exec/
│       └── e5f6g7h8.json        # Exec execution result
```

**Workflow Result Structure**:

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

### Git Hooks Integration

Configure hooks to trigger workflow in `.autopilot.yaml`:

```yaml
git_hooks:
  pre_commit: true
  post_commit: true
  pre_push: false

# Associated workflows
workflows:
  - name: commit-check
    steps:
      - name: lint
        command: ruff check .
      - name: test
        command: pytest
```

---

## 🧪 Development Guide

### Development Environment

```bash
# Clone repo
git clone https://github.com/packs/autopilot-core.git
cd autopilot-core

# Install (development mode)
pip install -e ".[dev]"

# Run tests
pytest

# Format code
ruff format .
ruff check .
```

### Adding New Skills

**1. Create skill directory structure**

```
skills/
└── my-skill/
    ├── SKILL.md
    └── scripts/
        └── run.py
```

**2. Write SKILL.md**

```markdown
# My Skill

## Function
Describe skill functionality

## Trigger Rules
- `*.py`: Primary trigger
- `*.json`: Optional trigger

## Usage
```bash
python skills/my-skill/scripts/run.py --arg value
```
```

**3. Write script**

```python
#!/usr/bin/env python3
"""My Skill"""

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="My Skill")
    parser.add_argument("--file", "-f", help="Target file")
    args = parser.parse_args()

    # Implement skill logic
    print("Running my skill...")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
```

### Extending Learning Engine

```python
from autopilot_core.core.learning_engine import LearningEngine

class CustomLearningEngine(LearningEngine):
    def custom_prediction(self, files, context):
        """Custom prediction logic"""
        # Analyze file history
        # Generate prediction
        return {
            "predicted_rate": 0.85,
            "confidence": 0.7,
            "risk": "low"
        }

# Use custom engine
engine = CustomLearningEngine(db_path=".autopilot/.learning.db")
result = engine.predict_for_files(["server.py"])
```

### API Integration

```python
from autopilot_core.core.autonomous import AutonomousScheduler, AutopilotConfig

# Create scheduler
config = AutopilotConfig(
    project_root=Path("/path/to/project"),
    learning_enabled=True,
    max_workers=3
)
scheduler = AutonomousScheduler(config=config)

# Run full cycle
success = scheduler.run_full_cycle(files=["server.py", "tests/"])

# Get results
print(scheduler.results)
```

---

## ❓ FAQ

### Q: How to uninstall?

```bash
pip uninstall autopilot-core
rm -rf ~/.autopilot  # Optional, delete global config
```

### Q: How to disable learning engine?

```bash
autopilot config set learning.enabled false
```

### Q: How to add custom notification channels?

Configure in `.autopilot.yaml`:

```yaml
notification:
  channels:
    - osascript
    - slack

slack:
  webhook_url: https://hooks.slack.com/...
```

### Q: How to view detailed execution logs?

```bash
# Dry run mode to view complete plan
autopilot run --dry-run -f server.py

# View status
autopilot status
```

### Q: How to contribute code?

1. Fork the repo
2. Create branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'feat: add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Create Pull Request

### Q: Which Python versions are supported?

- Python 3.8+
- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12

### Q: Which operating systems are supported?

- Linux (tested)
- macOS (tested)
- Windows (WSL compatible)

---

## 📦 Release Notes

### Suitable Projects

**Autopilot Core** is suitable for the following types of projects:

| Project Type | Description |
|-------------|-------------|
| **Needs CI/CD automation** | Auto-trigger testing, lint, deployment checks |
| **Has multi-step workflows** | Need to execute multiple external CLIs sequentially |
| **Needs unified recording** | Want to persist execution results for auditing |
| **Uses external governance tools** | Already has review CLI/security scan CLI, wants unified orchestration |
| **AI Agent integration** | Need to provide autonomous execution capability for Claude Code and other AI Agents |

**Not suitable for**:
- Complex DAG or conditional branching workflows (V2 planned)
- Projects needing review decision logic (autopilot-core only handles execution, not decision-making)
- Projects relying on specific tool output structured parsing

### Version Notes

| Version | Status | Description |
|---------|--------|-------------|
| V1.0 | ✅ Stable | Core functionality: workflow, exec, validate |
| V1.1 | ✅ Current | Added history, --json, test coverage |
| V2.0 | Planned | Conditional execution, variable passing, Dashboard integration |

---

## ⚠️ Known Limitations

1. **Workflow only supports sequential execution** - No parallel or DAG support
2. **No variable passing** - Cannot share state between steps
3. **No conditional branching** - Decide next step based on previous result (V2 planned)
4. **Tests are mostly unit-level** - No end-to-end integration tests
5. **Python 3.8+ only** - Python 3.7 not supported

---

## 📝 License

MIT License - See [LICENSE](LICENSE) file.

---

## 🙏 Acknowledgments

- [Claude Code](https://claude.ai/code) - AI programming assistant
- [MCP Protocol](https://modelcontextprotocol.io) - Model Context Protocol

---

<p align="center">
  <strong>Autopilot Core</strong> — Making Automation Smarter
</p>