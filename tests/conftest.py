#!/usr/bin/env python3
"""
测试配置和共享 fixtures
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

import pytest


@pytest.fixture
def temp_project(tmp_path):
    """
    创建一个临时项目目录，模拟真实的 autopilot 项目结构
    """
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    autopilot_dir = project_dir / ".autopilot"
    autopilot_dir.mkdir()

    state_dir = autopilot_dir / "state"
    state_dir.mkdir()

    yield project_dir

    # 清理由 pytest 自动处理


@pytest.fixture
def minimal_config():
    """最小有效配置"""
    return {
        "workflows": []
    }


@pytest.fixture
def sample_workflow_config():
    """示例 workflow 配置"""
    return {
        "workflows": [
            {
                "name": "test-workflow",
                "description": "A test workflow",
                "steps": [
                    {
                        "name": "step1",
                        "command": "echo 'step1'",
                        "timeout": 60
                    },
                    {
                        "name": "step2",
                        "command": "echo 'step2'",
                        "timeout": 60
                    }
                ]
            },
            {
                "name": "fail-workflow",
                "description": "A workflow that fails",
                "steps": [
                    {
                        "name": "fail-step",
                        "command": "python3 -c 'import sys; sys.exit(3)'",
                        "timeout": 60
                    }
                ]
            },
            {
                "name": "continue-workflow",
                "description": "A workflow that continues on error",
                "steps": [
                    {
                        "name": "fail-step",
                        "command": "python3 -c 'import sys; sys.exit(1)'",
                        "timeout": 60,
                        "continue_on_error": True
                    },
                    {
                        "name": "after-fail",
                        "command": "echo 'after'",
                        "timeout": 60
                    }
                ]
            },
            {
                "name": "workflow-level-continue",
                "description": "Workflow with workflow-level continue_on_error",
                "continue_on_error": True,
                "steps": [
                    {
                        "name": "step1-fail",
                        "command": "python3 -c 'import sys; sys.exit(1)'",
                        "timeout": 60
                    },
                    {
                        "name": "step2-run",
                        "command": "echo 'still running'",
                        "timeout": 60
                    }
                ]
            },
            {
                "name": "workflow-level-stop",
                "description": "Workflow with workflow-level continue_on_error=False",
                "continue_on_error": False,
                "steps": [
                    {
                        "name": "step1-fail",
                        "command": "python3 -c 'import sys; sys.exit(1)'",
                        "timeout": 60
                    },
                    {
                        "name": "step2-never",
                        "command": "echo 'never runs'",
                        "timeout": 60
                    }
                ]
            }
        ]
    }


def write_config(project_dir: Path, config: Dict[str, Any]):
    """写入配置文件"""
    import yaml
    config_path = project_dir / ".autopilot.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    return config_path


def write_exec_result(state_dir: Path, run_id: str, success: bool = True, exit_code: int = 0):
    """写入 exec 结果文件"""
    exec_dir = state_dir / "exec"
    exec_dir.mkdir(exist_ok=True)
    result = {
        "run_id": run_id,
        "command_name": "test",
        "command": "test command",
        "cwd": str(state_dir),
        "started_at": "2026-05-12T10:00:00",
        "duration_seconds": 0.01,
        "exit_code": exit_code,
        "success": success,
        "stdout_summary": "",
        "stderr_summary": ""
    }
    with open(exec_dir / f"{run_id}.json", "w") as f:
        json.dump(result, f)


def write_workflow_result(state_dir: Path, workflow_name: str, run_id: str, success: bool = True, exit_code: int = 0):
    """写入 workflow 结果文件"""
    wf_dir = state_dir / "workflows" / workflow_name
    wf_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "run_id": run_id,
        "workflow_name": workflow_name,
        "command": f"workflow: {workflow_name}",
        "cwd": str(state_dir),
        "started_at": "2026-05-12T10:00:00",
        "duration_seconds": 0.5,
        "exit_code": exit_code,
        "success": success,
        "steps": [],
        "failed_step": None if success else "step1",
        "completed_steps": ["step1"] if success else ["step1"]
    }
    with open(wf_dir / f"{run_id}.json", "w") as f:
        json.dump(result, f)
