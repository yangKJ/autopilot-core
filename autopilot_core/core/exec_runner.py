#!/usr/bin/env python3
"""
外部命令执行器
提供统一的外部CLI执行入口和结果落盘
"""

import subprocess
import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


# 结果摘要最大长度
MAX_SUMMARY_LENGTH = 2000


@dataclass
class ExecResult:
    """一次性命令执行结果"""
    run_id: str
    command_name: str
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
    def from_dict(cls, data: Dict) -> "ExecResult":
        return cls(**data)


class ExecRunner:
    """外部命令执行器"""

    def __init__(self, state_dir: Optional[Path] = None):
        self.state_dir = state_dir or Path(".autopilot/state")
        self.exec_results_dir = self.state_dir / "exec"
        self.exec_results_dir.mkdir(parents=True, exist_ok=True)

    def run_command(
        self,
        command: List[str],
        cwd: Optional[str] = None,
        timeout: int = 300,
        env: Optional[Dict[str, str]] = None,
    ) -> ExecResult:
        """执行外部命令并返回统一结果"""
        run_id = str(uuid.uuid4())[:8]
        started_at = datetime.now().isoformat()
        cwd = cwd or str(Path.cwd())

        # 构建命令字符串（用于显示）
        command_str = " ".join(command)
        command_name = command[0] if command else ""

        # 合并环境变量
        exec_env = None
        if env:
            exec_env = {**subprocess.os.environ.copy(), **env}

        # 执行命令
        start_time = datetime.now()
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
                env=exec_env,
            )
            exit_code = result.returncode
            success = exit_code == 0
            stdout = result.stdout or ""
            stderr = result.stderr or ""
        except subprocess.TimeoutExpired:
            exit_code = -1
            success = False
            stdout = ""
            stderr = f"Command timed out after {timeout} seconds"
        except Exception as e:
            exit_code = -2
            success = False
            stdout = ""
            stderr = str(e)

        duration = (datetime.now() - start_time).total_seconds()

        # 构建结果
        exec_result = ExecResult(
            run_id=run_id,
            command_name=command_name,
            command=command_str,
            cwd=cwd,
            started_at=started_at,
            duration_seconds=duration,
            exit_code=exit_code,
            success=success,
            stdout_summary=self._truncate(stdout),
            stderr_summary=self._truncate(stderr),
        )

        # 落盘
        self._save_result(exec_result)

        return exec_result

    def _truncate(self, text: str, max_length: int = MAX_SUMMARY_LENGTH) -> str:
        """截断过长输出"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + f"\n... (truncated, {len(text) - max_length} more chars)"

    def _save_result(self, result: ExecResult):
        """保存结果到文件"""
        result_file = self.exec_results_dir / f"{result.run_id}.json"
        with open(result_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

    def get_result(self, run_id: str) -> Optional[ExecResult]:
        """根据run_id获取执行结果"""
        result_file = self.exec_results_dir / f"{run_id}.json"
        if not result_file.exists():
            return None
        with open(result_file) as f:
            return ExecResult.from_dict(json.load(f))

    def list_results(self, limit: int = 20) -> List[ExecResult]:
        """列出最近的执行结果"""
        results = []
        for result_file in sorted(self.exec_results_dir.glob("*.json"), reverse=True)[:limit]:
            with open(result_file) as f:
                results.append(ExecResult.from_dict(json.load(f)))
        return results


def exec_command(
    command: List[str],
    cwd: Optional[str] = None,
    timeout: int = 300,
    env: Optional[Dict[str, str]] = None,
    verbose: bool = False,
    json_output: bool = False,
) -> int:
    """
    执行外部命令的便捷函数

    Returns:
        命令的原始exit code
    """
    import json
    runner = ExecRunner()

    # 确定工作目录
    if cwd is None:
        cwd = str(Path.cwd())

    if not json_output:
        print(f"\n{'='*60}")
        print(f"📦 执行外部命令")
        print(f"{'='*60}")
        print(f"📂 工作目录: {cwd}")
        print(f"⏱️  超时时间: {timeout}s")
        print(f"🔧 命令: {' '.join(command)}")
        print(f"{'='*60}\n")

    result = runner.run_command(command, cwd=cwd, timeout=timeout, env=env)

    if json_output:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return result.exit_code

    # 输出结果摘要
    print(f"\n{'='*60}")
    print(f"📊 执行结果")
    print(f"{'='*60}")
    print(f"状态: {'✅ 成功' if result.success else '❌ 失败'}")
    print(f"耗时: {result.duration_seconds:.2f}s")
    print(f"退出码: {result.exit_code}")

    if result.stdout_summary:
        print(f"\n📤 stdout ({len(result.stdout_summary)} chars):")
        print("-" * 40)
        print(result.stdout_summary)
        print("-" * 40)

    if result.stderr_summary:
        print(f"\n📕 stderr ({len(result.stderr_summary)} chars):")
        print("-" * 40)
        print(result.stderr_summary)
        print("-" * 40)

    print(f"\n💾 结果已落盘: {runner.exec_results_dir}/{result.run_id}.json")
    print(f"{'='*60}\n")

    return result.exit_code


# CLI 入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Autopilot 外部命令执行")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="要执行的命令")
    parser.add_argument("--cwd", "-C", help="工作目录")
    parser.add_argument("--timeout", "-t", type=int, default=300, help="超时时间(秒)")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
    else:
        exit_code = exec_command(args.command, cwd=args.cwd, timeout=args.timeout, verbose=args.verbose)
        exit(exit_code)
