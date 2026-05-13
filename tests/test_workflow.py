#!/usr/bin/env python3
"""
Workflow 和 Exec 相关测试
"""

import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

# 确保可以导入 autopilot_core
sys.path.insert(0, str(Path(__file__).parent.parent))

from autopilot_core.core.config import (
    AutopilotSettings,
    WorkflowDefinition,
    WorkflowStepConfig,
    ConfigLoader,
)
from autopilot_core.core.workflow_runner import WorkflowRunner, workflow_list, workflow_show, workflow_run
from autopilot_core.core.exec_runner import ExecRunner, exec_command


class TestWorkflowConfig:
    """测试 workflow 配置解析"""

    def test_workflow_step_config_from_dict(self):
        """测试 WorkflowStepConfig.from_dict"""
        data = {
            "name": "test-step",
            "command": "echo hello",
            "timeout": 120,
            "cwd": "/tmp",
            "continue_on_error": True,
            "env": {"KEY": "value"}
        }
        step = WorkflowStepConfig.from_dict(data)

        assert step.name == "test-step"
        assert step.command == "echo hello"
        assert step.timeout == 120
        assert step.cwd == "/tmp"
        assert step.continue_on_error is True
        assert step.env == {"KEY": "value"}

    def test_workflow_step_config_defaults(self):
        """测试 WorkflowStepConfig 默认值"""
        data = {
            "name": "test-step",
            "command": "echo hello"
        }
        step = WorkflowStepConfig.from_dict(data)

        assert step.timeout == 300
        assert step.cwd is None
        assert step.continue_on_error is False
        assert step.env is None

    def test_workflow_definition_from_dict(self):
        """测试 WorkflowDefinition.from_dict"""
        data = {
            "name": "test-workflow",
            "description": "Test description",
            "steps": [
                {"name": "step1", "command": "echo 1"},
                {"name": "step2", "command": "echo 2"}
            ]
        }
        wf = WorkflowDefinition.from_dict(data)

        assert wf.name == "test-workflow"
        assert wf.description == "Test description"
        assert len(wf.steps) == 2
        assert wf.steps[0].name == "step1"
        assert wf.steps[1].name == "step2"

    def test_autopilot_settings_workflows(self):
        """测试 AutopilotSettings 加载 workflows"""
        data = {
            "workflows": [
                {
                    "name": "wf1",
                    "description": "Workflow 1",
                    "steps": [{"name": "s1", "command": "echo 1"}]
                }
            ]
        }
        settings = AutopilotSettings.from_dict(data)

        assert len(settings.workflows) == 1
        assert settings.workflows[0].name == "wf1"


class TestWorkflowRunner:
    """测试 WorkflowRunner"""

    def test_list_workflows_empty(self, temp_project):
        """测试列出空工作流"""
        from autopilot_core.core.config import load_config

        # 写入空配置
        import yaml
        config_path = temp_project / ".autopilot.yaml"
        with open(config_path, "w") as f:
            yaml.dump({"workflows": []}, f)

        runner = WorkflowRunner()
        workflows = runner.list_workflows(temp_project)
        assert len(workflows) == 0

    def test_list_workflows(self, temp_project, sample_workflow_config):
        """测试列出工作流"""
        import yaml
        config_path = temp_project / ".autopilot.yaml"
        with open(config_path, "w") as f:
            yaml.dump(sample_workflow_config, f)

        runner = WorkflowRunner()
        workflows = runner.list_workflows(temp_project)

        assert len(workflows) == 5
        names = [wf.name for wf in workflows]
        assert "test-workflow" in names
        assert "fail-workflow" in names
        assert "continue-workflow" in names
        assert "workflow-level-continue" in names
        assert "workflow-level-stop" in names

    def test_show_workflow(self, temp_project, sample_workflow_config):
        """测试显示工作流详情"""
        import yaml
        config_path = temp_project / ".autopilot.yaml"
        with open(config_path, "w") as f:
            yaml.dump(sample_workflow_config, f)

        runner = WorkflowRunner()
        wf = runner.show_workflow("test-workflow", temp_project)

        assert wf is not None
        assert wf.name == "test-workflow"
        assert wf.description == "A test workflow"
        assert len(wf.steps) == 2

    def test_show_workflow_not_found(self, temp_project):
        """测试显示不存在的工作流"""
        import yaml
        config_path = temp_project / ".autopilot.yaml"
        with open(config_path, "w") as f:
            yaml.dump({"workflows": []}, f)

        runner = WorkflowRunner()
        wf = runner.show_workflow("nonexistent", temp_project)
        assert wf is None


class TestWorkflowExecution:
    """测试 workflow 执行"""

    def test_workflow_run_success(self, temp_project, sample_workflow_config):
        """测试 workflow 成功执行"""
        import yaml
        config_path = temp_project / ".autopilot.yaml"
        with open(config_path, "w") as f:
            yaml.dump(sample_workflow_config, f)

        runner = WorkflowRunner()
        result = runner.run_workflow("test-workflow", temp_project)

        assert result.success is True
        assert result.exit_code == 0
        assert result.failed_step is None
        assert len(result.completed_steps) == 2

    def test_workflow_run_fail_stop(self, temp_project, sample_workflow_config):
        """测试 workflow fail-stop"""
        import yaml
        config_path = temp_project / ".autopilot.yaml"
        with open(config_path, "w") as f:
            yaml.dump(sample_workflow_config, f)

        runner = WorkflowRunner()
        result = runner.run_workflow("fail-workflow", temp_project)

        assert result.success is False
        assert result.exit_code != 0
        assert result.failed_step == "fail-step"
        assert len(result.completed_steps) == 0

    def test_workflow_run_continue_on_error(self, temp_project, sample_workflow_config):
        """测试 workflow continue-on-error (step-level)"""
        import yaml
        config_path = temp_project / ".autopilot.yaml"
        with open(config_path, "w") as f:
            yaml.dump(sample_workflow_config, f)

        runner = WorkflowRunner()
        result = runner.run_workflow("continue-workflow", temp_project)

        # continue_on_error=True 时，整体状态仍为失败（有步骤失败了）
        assert result.success is False
        assert result.failed_step == "fail-step"
        # 但所有步骤都执行了
        assert len(result.completed_steps) == 2

    def test_workflow_level_continue_on_error(self, temp_project, sample_workflow_config):
        """测试 workflow-level continue_on_error=True"""
        import yaml
        config_path = temp_project / ".autopilot.yaml"
        with open(config_path, "w") as f:
            yaml.dump(sample_workflow_config, f)

        runner = WorkflowRunner()
        result = runner.run_workflow("workflow-level-continue", temp_project)

        # 工作流级别 continue_on_error=True，即使步骤失败也应继续
        assert result.success is False  # 有失败步骤
        assert result.failed_step == "step1-fail"
        # 所有步骤都执行了
        assert len(result.completed_steps) == 2
        assert "step2-run" in result.completed_steps

    def test_workflow_level_stop_on_error(self, temp_project, sample_workflow_config):
        """测试 workflow-level continue_on_error=False"""
        import yaml
        config_path = temp_project / ".autopilot.yaml"
        with open(config_path, "w") as f:
            yaml.dump(sample_workflow_config, f)

        runner = WorkflowRunner()
        result = runner.run_workflow("workflow-level-stop", temp_project)

        # 工作流级别 continue_on_error=False，失败时中止
        assert result.success is False
        assert result.exit_code != 0
        assert result.failed_step == "step1-fail"
        # 失败的步骤不会加入 completed_steps（因为工作流停止了）
        assert len(result.completed_steps) == 0
        assert "step2-never" not in result.completed_steps

    def test_workflow_level_continue_overrides_step(self, temp_project):
        """测试步骤级别的 continue_on_error 被工作流级别覆盖"""
        import yaml
        config_path = temp_project / ".autopilot.yaml"
        with open(config_path, "w") as f:
            yaml.dump({
                "workflows": [
                    {
                        "name": "override-test",
                        "description": "Test override",
                        "continue_on_error": True,  # 工作流级别=True
                        "steps": [
                            {
                                "name": "fail-step",
                                "command": "python3 -c 'import sys; sys.exit(1)'",
                                "continue_on_error": False  # 步骤级别=False，但应该被覆盖
                            },
                            {
                                "name": "after-step",
                                "command": "echo 'after'"
                            }
                        ]
                    }
                ]
            }, f)

        runner = WorkflowRunner()
        result = runner.run_workflow("override-test", temp_project)

        # 工作流级别 True 优先，应该继续执行
        assert result.success is False
        assert len(result.completed_steps) == 2

    def test_workflow_result_serialization(self, temp_project, sample_workflow_config):
        """测试结果 JSON 序列化"""
        import yaml
        config_path = temp_project / ".autopilot.yaml"
        with open(config_path, "w") as f:
            yaml.dump(sample_workflow_config, f)

        runner = WorkflowRunner()
        result = runner.run_workflow("test-workflow", temp_project)

        # 转换为 dict 并验证
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["workflow_name"] == "test-workflow"
        assert "run_id" in result_dict
        assert "started_at" in result_dict
        assert "steps" in result_dict

        # 验证可以反序列化
        from autopilot_core.core.workflow_runner import WorkflowResult
        restored = WorkflowResult.from_dict(result_dict)
        assert restored.run_id == result.run_id
        assert restored.workflow_name == result.workflow_name


class TestExecRunner:
    """测试 ExecRunner"""

    def test_exec_success(self, temp_project):
        """测试 exec 成功执行"""
        runner = ExecRunner(temp_project / ".autopilot" / "state")
        result = runner.run_command(["echo", "hello"])

        assert result.success is True
        assert result.exit_code == 0
        assert "hello" in result.stdout_summary

    def test_exec_failure(self, temp_project):
        """测试 exec 失败"""
        runner = ExecRunner(temp_project / ".autopilot" / "state")
        result = runner.run_command(["python3", "-c", "import sys; sys.exit(7)"])

        assert result.success is False
        assert result.exit_code == 7

    def test_exec_result_serialization(self, temp_project):
        """测试 exec 结果序列化"""
        runner = ExecRunner(temp_project / ".autopilot" / "state")
        result = runner.run_command(["echo", "test"])

        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "run_id" in result_dict
        assert "command" in result_dict
        assert "success" in result_dict

        from autopilot_core.core.exec_runner import ExecResult
        restored = ExecResult.from_dict(result_dict)
        assert restored.run_id == result.run_id


class TestWorkflowValidation:
    """测试 workflow 校验"""

    def test_validate_workflow_step_missing_name(self):
        """测试步骤缺少 name"""
        from autopilot_core.core.workflow_runner import WorkflowRunner

        runner = WorkflowRunner()
        result = runner._validate_step({"command": "echo hello"})
        assert result["valid"] is False
        assert "name" in result["errors"][0].lower()

    def test_validate_workflow_step_missing_command(self):
        """测试步骤缺少 command"""
        from autopilot_core.core.workflow_runner import WorkflowRunner

        runner = WorkflowRunner()
        result = runner._validate_step({"name": "step1"})
        assert result["valid"] is False
        assert "command" in result["errors"][0].lower()

    def test_validate_workflow_step_valid(self):
        """测试步骤有效"""
        from autopilot_core.core.workflow_runner import WorkflowRunner

        runner = WorkflowRunner()
        result = runner._validate_step({
            "name": "step1",
            "command": "echo hello",
            "timeout": 60
        })
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_workflow_invalid_timeout(self):
        """测试无效的 timeout"""
        from autopilot_core.core.workflow_runner import WorkflowRunner

        runner = WorkflowRunner()
        result = runner._validate_step({
            "name": "step1",
            "command": "echo hello",
            "timeout": -1
        })
        assert result["valid"] is False


class TestExecTimeout:
    """测试 exec timeout"""

    def test_exec_timeout(self, temp_project):
        """测试 exec 超时"""
        runner = ExecRunner(temp_project / ".autopilot" / "state")
        # 使用一个会超时的命令：sleep 2 + timeout 1
        result = runner.run_command(["python3", "-c", "import time; time.sleep(10)"], timeout=1)

        assert result.success is False
        assert result.exit_code == -1  # timeout exit code
        assert "timed out" in result.stderr_summary.lower()


class TestCLIErrorPaths:
    """测试 CLI 错误路径"""

    def test_workflow_run_missing_workflow_json(self, temp_project, sample_workflow_config):
        """测试 workflow run --json 时工作流不存在"""
        import yaml
        import subprocess
        config_path = temp_project / ".autopilot.yaml"
        with open(config_path, "w") as f:
            yaml.dump(sample_workflow_config, f)

        result = subprocess.run(
            [sys.executable, "-m", "autopilot_core.cli", "workflow", "run", "nonexistent", "--json"],
            cwd=temp_project,
            capture_output=True,
            text=True
        )

        # 应该返回非0退出码
        assert result.returncode != 0
        # JSON输出应该不包含人类可读文字
        lines = result.stdout.strip().split('\n')
        import json
        try:
            output = json.loads('\n'.join(lines))
            assert output["success"] is False
            assert output["workflow_name"] == "nonexistent"
        except json.JSONDecodeError:
            # 如果JSON解析失败，说明输出被污染了
            assert False, f"JSON output was corrupted: {result.stdout}"

    def test_workflow_history_empty(self, temp_project):
        """测试 workflow history 为空"""
        import yaml
        import subprocess
        config_path = temp_project / ".autopilot.yaml"
        with open(config_path, "w") as f:
            yaml.dump({"workflows": []}, f)

        result = subprocess.run(
            [sys.executable, "-m", "autopilot_core.cli", "workflow", "history", "test-wf"],
            cwd=temp_project,
            capture_output=True,
            text=True
        )

        # 应该返回0（没有历史记录不是错误）
        assert result.returncode == 0
        assert "暂无执行记录" in result.stdout

    def test_workflow_validate_invalid_config(self, temp_project):
        """测试 workflow validate 无效配置"""
        import yaml
        import subprocess
        config_path = temp_project / ".autopilot.yaml"
        with open(config_path, "w") as f:
            yaml.dump({"workflows": [{"name": "bad", "steps": []}]}, f)  # steps为空

        result = subprocess.run(
            [sys.executable, "-m", "autopilot_core.cli", "workflow", "validate"],
            cwd=temp_project,
            capture_output=True,
            text=True
        )

        # 应该返回非0
        assert result.returncode != 0
        assert "校验失败" in result.stdout

    def test_exec_failure_json(self, temp_project):
        """测试 exec --json 时命令失败"""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "autopilot_core.cli", "exec", "--json", "--",
             "python3", "-c", "import sys; sys.exit(7)"],
            cwd=temp_project,
            capture_output=True,
            text=True
        )

        # 应该返回7
        assert result.returncode == 7
        # 验证JSON输出
        import json
        output = json.loads(result.stdout)
        assert output["success"] is False
        assert output["exit_code"] == 7

    def test_exec_success_json(self, temp_project):
        """测试 exec --json 时命令成功"""
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "autopilot_core.cli", "exec", "--json", "--",
             "echo", "hello"],
            cwd=temp_project,
            capture_output=True,
            text=True
        )

        # 应该返回0
        assert result.returncode == 0
        # 验证JSON输出
        import json
        output = json.loads(result.stdout)
        assert output["success"] is True
        assert "hello" in output["stdout_summary"]


class TestLayeredConfig:
    """测试分层配置"""

    def test_validate_with_local_only_config(self, temp_project):
        """测试只有本地配置时 validate 仍能工作"""
        import yaml
        # 只创建 .autopilot.local.yaml，不创建 .autopilot.yaml
        local_config_path = temp_project / ".autopilot.local.yaml"
        with open(local_config_path, "w") as f:
            yaml.dump({
                "workflows": [
                    {"name": "local-wf", "description": "Local workflow", "steps": [
                        {"name": "step1", "command": "echo local"}
                    ]}
                ]
            }, f)

        from autopilot_core.core.workflow_runner import WorkflowRunner, workflow_validate
        runner = WorkflowRunner()

        # list 应该能找到工作流
        workflows = runner.list_workflows(temp_project)
        assert len(workflows) == 1
        assert workflows[0].name == "local-wf"

        # validate 也应该能找到工作流
        result = runner.validate_config({"workflows": [{"name": "local-wf", "steps": [{"name": "s1", "command": "echo"}]}]})
        assert result["valid"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
