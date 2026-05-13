#!/usr/bin/env python3
"""
外部工作流执行引擎
支持顺序执行步骤、统一结果落盘、失败中断
"""

import json
import shlex
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from .config import WorkflowDefinition, WorkflowStepConfig, load_workflow
from .exec_runner import ExecRunner, ExecResult


# 结果摘要最大长度
MAX_SUMMARY_LENGTH = 2000


@dataclass
class StepResult:
    """工作流步骤执行结果"""
    step_name: str
    command: str
    cwd: str
    started_at: str
    duration_seconds: float
    exit_code: int
    success: bool
    stdout_summary: str
    stderr_summary: str

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "StepResult":
        return cls(**data)


@dataclass
class WorkflowResult:
    """工作流执行结果"""
    run_id: str
    workflow_name: str
    command: str  # 完整命令字符串
    cwd: str
    started_at: str
    duration_seconds: float
    exit_code: int
    success: bool
    steps: List[StepResult] = field(default_factory=list)
    failed_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "WorkflowResult":
        steps = [StepResult.from_dict(s) for s in data.get("steps", [])]
        return cls(
            run_id=data["run_id"],
            workflow_name=data["workflow_name"],
            command=data["command"],
            cwd=data["cwd"],
            started_at=data["started_at"],
            duration_seconds=data["duration_seconds"],
            exit_code=data["exit_code"],
            success=data["success"],
            steps=steps,
            failed_step=data.get("failed_step"),
            completed_steps=data.get("completed_steps", []),
        )


class WorkflowRunner:
    """外部工作流执行器"""

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or Path(".autopilot/state")
        self.workflow_results_dir = self.state_dir / "workflows"
        self.workflow_results_dir.mkdir(parents=True, exist_ok=True)
        self.exec_runner = ExecRunner(state_dir)

    def load_workflow(self, name: str, project_root: Optional[Path] = None) -> Optional[WorkflowDefinition]:
        """加载工作流定义"""
        return load_workflow(name, project_root)

    def list_workflows(self, project_root: Optional[Path] = None) -> List[WorkflowDefinition]:
        """列出所有工作流"""
        from .config import load_config
        settings = load_config(project_root)
        return settings.workflows

    def show_workflow(self, name: str, project_root: Optional[Path] = None) -> Optional[WorkflowDefinition]:
        """显示工作流详情"""
        return self.load_workflow(name, project_root)

    def run_workflow(
        self,
        workflow_name: str,
        project_root: Optional[Path] = None,
        verbose: bool = False,
        json_output: bool = False,
    ) -> WorkflowResult:
        """执行工作流"""
        run_id = str(uuid.uuid4())[:8]
        started_at = datetime.now().isoformat()
        project_root = project_root or Path.cwd()
        cwd = str(project_root)

        # 加载工作流定义
        workflow = self.load_workflow(workflow_name, project_root)
        if not workflow:
            return self._create_not_found_result(
                run_id, workflow_name, cwd, started_at, f"Workflow '{workflow_name}' not found",
                json_output=json_output
            )

        if not json_output:
            print(f"\n{'='*60}")
            print(f"🚀 开始执行工作流: {workflow_name}")
            print(f"{'='*60}")
            print(f"📝 描述: {workflow.description}")
            print(f"📂 工作目录: {cwd}")
            print(f"📊 步骤数: {len(workflow.steps)}")
            print(f"{'='*60}\n")

        steps_results: List[StepResult] = []
        completed_steps: List[str] = []
        failed_step: Optional[str] = None
        overall_success = True
        workflow_exit_code = 0
        has_failures = False  # 追踪是否有步骤失败

        # 顺序执行每个步骤
        for i, step_config in enumerate(workflow.steps, 1):
            if not json_output:
                print(f"\n{'='*60}")
                print(f"📌 步骤 {i}/{len(workflow.steps)}: {step_config.name}")
                print(f"{'='*60}")

            step_result = self._run_step(step_config, cwd, verbose, json_output=json_output)
            steps_results.append(step_result)

            # 输出步骤结果
            if not json_output:
                print(f"\n{'='*60}")
                print(f"📊 步骤结果")
                print(f"{'='*60}")
                print(f"状态: {'✅ 成功' if step_result.success else '❌ 失败'}")
                print(f"耗时: {step_result.duration_seconds:.2f}s")
                print(f"退出码: {step_result.exit_code}")

                if step_result.stdout_summary:
                    print(f"\n📤 stdout ({len(step_result.stdout_summary)} chars):")
                    print("-" * 40)
                    print(step_result.stdout_summary)
                    print("-" * 40)

                if step_result.stderr_summary:
                    print(f"\n📕 stderr ({len(step_result.stderr_summary)} chars):")
                    print("-" * 40)
                    print(step_result.stderr_summary)
                    print("-" * 40)

            # 判断是否继续
            if not step_result.success:
                has_failures = True
                failed_step = step_config.name
                workflow_exit_code = step_result.exit_code
                overall_success = False  # 有失败步骤，整体失败

                # 优先使用步骤级别的 continue_on_error，否则使用工作流级别的
                step_continue = step_config.continue_on_error
                workflow_continue = workflow.continue_on_error

                if not step_continue and not workflow_continue:
                    if not json_output:
                        print(f"\n⚠️  步骤失败且 continue_on_error=False，中止工作流")
                    break
                else:
                    if not json_output:
                        reason = "步骤" if step_continue else "工作流"
                        print(f"\n⚠️  步骤失败但 {reason} continue_on_error=True，继续执行")
                    # 即使继续，也将失败的步骤加入completed_steps
                    completed_steps.append(step_config.name)
            else:
                completed_steps.append(step_config.name)

        # 计算总耗时
        total_duration = sum(s.duration_seconds for s in steps_results)

        # 构建工作流结果
        workflow_result = WorkflowResult(
            run_id=run_id,
            workflow_name=workflow_name,
            command=f"workflow: {workflow_name}",
            cwd=cwd,
            started_at=started_at,
            duration_seconds=total_duration,
            exit_code=workflow_exit_code,
            success=overall_success,
            steps=steps_results,
            failed_step=failed_step,
            completed_steps=completed_steps,
        )

        # 落盘
        self._save_result(workflow_result)

        # 输出总结
        if not json_output:
            print(f"\n\n{'='*60}")
            print(f"🏁 工作流执行完成")
            print(f"{'='*60}")
            print(f"状态: {'✅ 成功' if workflow_result.success else '❌ 失败'}")
            print(f"总耗时: {workflow_result.duration_seconds:.2f}s")
            print(f"完成步骤: {len(workflow_result.completed_steps)}/{len(workflow.steps)}")

            if workflow_result.failed_step:
                print(f"失败步骤: {workflow_result.failed_step}")

            print(f"💾 结果已落盘: {self._get_result_dir(workflow_name)}/{run_id}.json")
            print(f"{'='*60}\n")

        return workflow_result

    def _run_step(
        self,
        step_config: WorkflowStepConfig,
        default_cwd: str,
        verbose: bool = False,
        json_output: bool = False,
    ) -> StepResult:
        """执行单个步骤"""
        started_at = datetime.now().isoformat()
        cwd = step_config.cwd or default_cwd

        # 构建命令列表（使用shlex正确处理引号）
        command = shlex.split(step_config.command)

        if not json_output:
            print(f"🔧 执行命令: {step_config.command}")
            print(f"📂 工作目录: {cwd}")
            print(f"⏱️  超时: {step_config.timeout}s")

        # 使用exec_runner执行
        exec_result = self.exec_runner.run_command(
            command,
            cwd=cwd,
            timeout=step_config.timeout,
            env=step_config.env,
        )

        return StepResult(
            step_name=step_config.name,
            command=step_config.command,
            cwd=cwd,
            started_at=started_at,
            duration_seconds=exec_result.duration_seconds,
            exit_code=exec_result.exit_code,
            success=exec_result.success,
            stdout_summary=exec_result.stdout_summary,
            stderr_summary=exec_result.stderr_summary,
        )

    def _create_not_found_result(
        self,
        run_id: str,
        workflow_name: str,
        cwd: str,
        started_at: str,
        error_message: str,
        json_output: bool = False,
    ) -> WorkflowResult:
        """创建工作流未找到时的结果"""
        result = WorkflowResult(
            run_id=run_id,
            workflow_name=workflow_name,
            command=f"workflow: {workflow_name}",
            cwd=cwd,
            started_at=started_at,
            duration_seconds=0,
            exit_code=-1,
            success=False,
            steps=[],
            failed_step=None,
            completed_steps=[],
        )
        self._save_result(result)
        if not json_output:
            print(f"\n❌ {error_message}")
        return result

    def _save_result(self, result: WorkflowResult):
        """保存工作流结果"""
        result_dir = self._get_result_dir(result.workflow_name)
        result_dir.mkdir(parents=True, exist_ok=True)
        result_file = result_dir / f"{result.run_id}.json"
        with open(result_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

    def _get_result_dir(self, workflow_name: str) -> Path:
        """获取工作流结果目录"""
        safe_name = workflow_name.replace("/", "_").replace("\\", "_")
        return self.workflow_results_dir / safe_name

    def get_result(self, workflow_name: str, run_id: str) -> Optional[WorkflowResult]:
        """获取指定工作流运行结果"""
        result_file = self._get_result_dir(workflow_name) / f"{run_id}.json"
        if not result_file.exists():
            return None
        with open(result_file) as f:
            return WorkflowResult.from_dict(json.load(f))

    def list_results(self, workflow_name: str, limit: int = 20) -> List[WorkflowResult]:
        """列出工作流的历史执行结果"""
        results = []
        result_dir = self._get_result_dir(workflow_name)
        if not result_dir.exists():
            return results

        for result_file in sorted(result_dir.glob("*.json"), reverse=True)[:limit]:
            with open(result_file) as f:
                results.append(WorkflowResult.from_dict(json.load(f)))
        return results

    def _validate_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """校验单个步骤配置"""
        errors = []

        if not step.get("name"):
            errors.append("step missing 'name'")
        if not step.get("command"):
            errors.append("step missing 'command'")

        timeout = step.get("timeout")
        if timeout is not None and (not isinstance(timeout, int) or timeout <= 0):
            errors.append("step 'timeout' must be a positive integer")

        continue_on_error = step.get("continue_on_error")
        if continue_on_error is not None and not isinstance(continue_on_error, bool):
            errors.append("step 'continue_on_error' must be a boolean")

        cwd = step.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            errors.append("step 'cwd' must be a string")

        env = step.get("env")
        if env is not None and not isinstance(env, dict):
            errors.append("step 'env' must be a dictionary")

        return {"valid": len(errors) == 0, "errors": errors}

    def validate_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """校验 workflow 配置"""
        errors = []

        name = workflow_data.get("name")
        if not name:
            errors.append("workflow missing 'name'")

        steps = workflow_data.get("steps", [])
        if not isinstance(steps, list):
            errors.append("workflow 'steps' must be a list")
        elif len(steps) == 0:
            errors.append("workflow 'steps' must not be empty")
        else:
            for i, step in enumerate(steps):
                step_result = self._validate_step(step)
                if not step_result["valid"]:
                    for error in step_result["errors"]:
                        errors.append(f"step {i} ({step.get('name', 'unknown')}): {error}")

        description = workflow_data.get("description")
        if description is not None and not isinstance(description, str):
            errors.append("workflow 'description' must be a string")

        continue_on_error = workflow_data.get("continue_on_error")
        if continue_on_error is not None and not isinstance(continue_on_error, bool):
            errors.append("workflow 'continue_on_error' must be a boolean")

        return {"valid": len(errors) == 0, "errors": errors}

    def validate_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """校验完整配置"""
        errors = []

        workflows = config_data.get("workflows", [])
        if not isinstance(workflows, list):
            errors.append("'workflows' must be a list")
        else:
            for i, wf in enumerate(workflows):
                wf_result = self.validate_workflow(wf)
                if not wf_result["valid"]:
                    for error in wf_result["errors"]:
                        errors.append(f"workflow '{wf.get('name', i)}': {error}")

        return {"valid": len(errors) == 0, "errors": errors, "workflow_count": len(workflows)}


def workflow_list(project_root: Optional[Path] = None, json_output: bool = False) -> int:
    """列出所有工作流的便捷函数"""
    import json
    runner = WorkflowRunner()
    workflows = runner.list_workflows(project_root)

    if json_output:
        result = {
            "workflows": [wf.to_dict() for wf in workflows],
            "count": len(workflows)
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if not workflows:
        print(f"\n📋 未配置任何工作流")
        print(f"请在 .autopilot.yaml 中添加 workflows 配置")
        return 0

    print(f"\n{'='*60}")
    print(f"📋 已配置的工作流 ({len(workflows)})")
    print(f"{'='*60}")

    for wf in workflows:
        print(f"\n📦 {wf.name}")
        print(f"   描述: {wf.description}")
        print(f"   步骤数: {len(wf.steps)}")
        for step in wf.steps:
            print(f"   - {step.name}: {step.command[:50]}{'...' if len(step.command) > 50 else ''}")

    print(f"\n{'='*60}\n")
    return 0


def workflow_show(workflow_name: str, project_root: Optional[Path] = None, json_output: bool = False) -> int:
    """显示工作流详情的便捷函数"""
    import json
    runner = WorkflowRunner()
    workflow = runner.show_workflow(workflow_name, project_root)

    if not workflow:
        if json_output:
            print(json.dumps({"error": f"workflow '{workflow_name}' not found"}, indent=2))
        else:
            print(f"\n❌ 工作流 '{workflow_name}' 未找到")
        return 1

    if json_output:
        print(json.dumps(workflow.to_dict(), indent=2, ensure_ascii=False))
        return 0

    print(f"\n{'='*60}")
    print(f"📦 工作流: {workflow.name}")
    print(f"{'='*60}")
    print(f"📝 描述: {workflow.description}")
    print(f"   失败继续: {'是' if workflow.continue_on_error else '否'} (工作流级别)")
    print(f"\n📊 步骤 ({len(workflow.steps)}):")

    for i, step in enumerate(workflow.steps, 1):
        print(f"\n  步骤 {i}: {step.name}")
        print(f"    命令: {step.command}")
        print(f"    超时: {step.timeout}s")
        print(f"    工作目录: {step.cwd or '(继承)'}")
        print(f"    失败继续: {'是' if step.continue_on_error else '否'}")

    print(f"\n{'='*60}\n")
    return 0


def workflow_run(
    workflow_name: str,
    project_root: Optional[Path] = None,
    verbose: bool = False,
    json_output: bool = False,
) -> int:
    """运行工作流的便捷函数"""
    import json
    runner = WorkflowRunner()
    result = runner.run_workflow(workflow_name, project_root, verbose, json_output=json_output)

    if json_output:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

    return 0 if result.success else 1


def workflow_history(
    workflow_name: str,
    project_root: Optional[Path] = None,
    limit: int = 10,
    json_output: bool = False,
) -> int:
    """查看工作流历史"""
    import json
    runner = WorkflowRunner()
    results = runner.list_results(workflow_name, limit)

    if json_output:
        print(json.dumps({
            "workflow_name": workflow_name,
            "runs": [r.to_dict() for r in results],
            "count": len(results)
        }, indent=2, ensure_ascii=False))
        return 0

    if not results:
        print(f"\n📋 工作流 '{workflow_name}' 暂无执行记录")
        return 0

    print(f"\n{'='*60}")
    print(f"📋 工作流 '{workflow_name}' 执行历史 (最近 {len(results)} 条)")
    print(f"{'='*60}")

    for r in results:
        status = "✅" if r.success else "❌"
        print(f"\n{status} run_id: {r.run_id}")
        print(f"   开始时间: {r.started_at}")
        print(f"   耗时: {r.duration_seconds:.2f}s")
        print(f"   退出码: {r.exit_code}")
        if r.failed_step:
            print(f"   失败步骤: {r.failed_step}")

    print(f"\n{'='*60}\n")
    return 0


def workflow_validate(
    project_root: Optional[Path] = None,
    json_output: bool = False,
) -> int:
    """校验工作流配置（支持分层配置）"""
    import json
    from .config import ConfigLoader

    project_root = project_root or Path.cwd()

    # 使用 ConfigLoader 加载配置，支持分层配置（全局/项目/本地）
    loader = ConfigLoader(project_root)

    # 检查是否有任何配置文件存在
    has_config = (
        loader.global_config_path.exists() or
        loader.project_config_path.exists() or
        loader.local_config_path.exists()
    )

    if not has_config:
        if json_output:
            print(json.dumps({"valid": False, "errors": ["no config file found"]}, indent=2))
        else:
            print(f"\n❌ 未找到任何配置文件")
        return 1

    try:
        settings = loader.load()
    except Exception as e:
        if json_output:
            print(json.dumps({"valid": False, "errors": [str(e)]}, indent=2))
        else:
            print(f"\n❌ 配置加载失败: {e}")
        return 1

    # 将 settings 转为 dict 供校验
    config_data = settings.to_dict()
    workflows_data = config_data.get("workflows", [])

    runner = WorkflowRunner()
    result = runner.validate_config({"workflows": workflows_data})

    if json_output:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["valid"] else 1

    if result["valid"]:
        print(f"\n✅ 配置校验通过")
        print(f"   工作流数量: {result['workflow_count']}")
    else:
        print(f"\n❌ 配置校验失败，发现 {len(result['errors'])} 个问题:")
        for error in result["errors"]:
            print(f"   - {error}")

    return 0 if result["valid"] else 1


# CLI 入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Autopilot 工作流管理")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # list - 列出工作流
    list_parser = subparsers.add_parser("list", help="列出所有工作流")
    list_parser.add_argument("--project-root", "-p", type=Path, default=Path.cwd(), help="项目根目录")

    # show - 显示工作流详情
    show_parser = subparsers.add_parser("show", help="显示工作流详情")
    show_parser.add_argument("name", help="工作流名称")
    show_parser.add_argument("--project-root", "-p", type=Path, default=Path.cwd(), help="项目根目录")

    # run - 运行工作流
    run_parser = subparsers.add_parser("run", help="运行工作流")
    run_parser.add_argument("name", help="工作流名称")
    run_parser.add_argument("--project-root", "-p", type=Path, default=Path.cwd(), help="项目根目录")
    run_parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    if args.command == "list":
        exit(workflow_list(args.project_root))
    elif args.command == "show":
        exit(workflow_show(args.name, args.project_root))
    elif args.command == "run":
        exit(workflow_run(args.name, args.project_root, args.verbose))
    else:
        parser.print_help()
