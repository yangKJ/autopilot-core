#!/usr/bin/env python3
"""
分层配置系统
支持：全局 ~/.autopilot/config.yaml + 项目 .autopilot.yaml + 本地 .autopilot.local.yaml
优先级：本地 > 项目 > 全局
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class WorkflowStepConfig:
    """工作流步骤配置"""
    name: str
    command: str
    timeout: int = 300
    cwd: Optional[str] = None
    continue_on_error: bool = False
    env: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "command": self.command,
            "timeout": self.timeout,
            "cwd": self.cwd,
            "continue_on_error": self.continue_on_error,
            "env": self.env,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "WorkflowStepConfig":
        return cls(
            name=data.get("name", ""),
            command=data.get("command", ""),
            timeout=data.get("timeout", 300),
            cwd=data.get("cwd"),
            continue_on_error=data.get("continue_on_error", False),
            env=data.get("env"),
        )


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    name: str
    description: str
    steps: List[WorkflowStepConfig] = field(default_factory=list)
    continue_on_error: bool = False  # 工作流级别失败继续设置

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() if isinstance(s, WorkflowStepConfig) else s for s in self.steps],
            "continue_on_error": self.continue_on_error,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "WorkflowDefinition":
        steps = [WorkflowStepConfig.from_dict(s) for s in data.get("steps", [])]
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=steps,
            continue_on_error=data.get("continue_on_error", False),
        )


@dataclass
class AutopilotSettings:
    """自动驾驶设置"""
    # 通用设置
    verbose: bool = False
    dry_run: bool = False

    # 学习引擎
    learning_enabled: bool = True
    min_samples: int = 3
    db_path: str = ".autopilot/.learning.db"

    # 执行引擎
    max_workers: int = 3
    timeout: int = 300
    retry_on_fail: bool = True

    # 监控
    debounce_seconds: int = 10
    max_batch: int = 30

    # 通知
    notification_enabled: bool = True
    notification_channels: List[str] = field(default_factory=lambda: ["osascript"])

    # 自愈
    auto_heal_enabled: bool = True
    max_heal_cycles: int = 3

    # 外部工作流
    workflows: List[WorkflowDefinition] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "verbose": self.verbose,
            "dry_run": self.dry_run,
            "learning": {
                "enabled": self.learning_enabled,
                "min_samples": self.min_samples,
                "db_path": self.db_path,
            },
            "executor": {
                "max_workers": self.max_workers,
                "timeout": self.timeout,
                "retry_on_fail": self.retry_on_fail,
            },
            "monitor": {
                "debounce_seconds": self.debounce_seconds,
                "max_batch": self.max_batch,
            },
            "notification": {
                "enabled": self.notification_enabled,
                "channels": self.notification_channels,
            },
            "auto_heal": {
                "enabled": self.auto_heal_enabled,
                "max_cycles": self.max_heal_cycles,
            },
            "workflows": [w.to_dict() if isinstance(w, WorkflowDefinition) else w for w in self.workflows],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AutopilotSettings":
        settings = cls()
        if "verbose" in data:
            settings.verbose = data["verbose"]
        if "dry_run" in data:
            settings.dry_run = data["dry_run"]

        learning = data.get("learning", {})
        settings.learning_enabled = learning.get("enabled", True)
        settings.min_samples = learning.get("min_samples", 3)
        settings.db_path = learning.get("db_path", ".autopilot/.learning.db")

        executor = data.get("executor", {})
        settings.max_workers = executor.get("max_workers", 3)
        settings.timeout = executor.get("timeout", 300)
        settings.retry_on_fail = executor.get("retry_on_fail", True)

        monitor = data.get("monitor", {})
        settings.debounce_seconds = monitor.get("debounce_seconds", 10)
        settings.max_batch = monitor.get("max_batch", 30)

        notification = data.get("notification", {})
        settings.notification_enabled = notification.get("enabled", True)
        settings.notification_channels = notification.get("channels", ["osascript"])

        auto_heal = data.get("auto_heal", {})
        settings.auto_heal_enabled = auto_heal.get("enabled", True)
        settings.max_heal_cycles = auto_heal.get("max_cycles", 3)

        # 加载工作流配置
        workflows_data = data.get("workflows", [])
        settings.workflows = [WorkflowDefinition.from_dict(w) for w in workflows_data]

        return settings


class ConfigLoader:
    """分层配置加载器"""

    GLOBAL_CONFIG_NAME = "~/.autopilot/config.yaml"
    PROJECT_CONFIG_NAME = ".autopilot.yaml"
    LOCAL_CONFIG_NAME = ".autopilot.local.yaml"

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.global_config_path = Path(self.GLOBAL_CONFIG_NAME).expanduser()
        self.project_config_path = self.project_root / self.PROJECT_CONFIG_NAME
        self.local_config_path = self.project_root / self.LOCAL_CONFIG_NAME

    def load(self) -> AutopilotSettings:
        """加载分层配置（优先级：本地 > 项目 > 全局）"""
        config_data: Dict[str, Any] = {}

        # 1. 加载全局配置（最低优先级）
        if self.global_config_path.exists():
            try:
                with open(self.global_config_path) as f:
                    data = yaml.safe_load(f) or {}
                    config_data = self._merge_config(config_data, data)
            except Exception as e:
                print(f"⚠️  全局配置加载失败: {e}")

        # 2. 加载项目配置
        if self.project_config_path.exists():
            try:
                with open(self.project_config_path) as f:
                    data = yaml.safe_load(f) or {}
                    config_data = self._merge_config(config_data, data)
            except Exception as e:
                print(f"⚠️  项目配置加载失败: {e}")

        # 3. 加载本地配置（最高优先级）
        if self.local_config_path.exists():
            try:
                with open(self.local_config_path) as f:
                    data = yaml.safe_load(f) or {}
                    config_data = self._merge_config(config_data, data)
            except Exception as e:
                print(f"⚠️  本地配置加载失败: {e}")

        return AutopilotSettings.from_dict(config_data)

    def _merge_config(self, base: Dict, overlay: Dict) -> Dict:
        """递归合并配置"""
        result = dict(base)
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result

    def save_global(self, settings: AutopilotSettings):
        """保存全局配置"""
        self.global_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.global_config_path, "w") as f:
            yaml.dump(settings.to_dict(), f, default_flow_style=False)
        print(f"✅ 全局配置已保存到 {self.global_config_path}")

    def save_project(self, settings: AutopilotSettings):
        """保存项目配置"""
        with open(self.project_config_path, "w") as f:
            yaml.dump(settings.to_dict(), f, default_flow_style=False)
        print(f"✅ 项目配置已保存到 {self.project_config_path}")

    def save_local(self, settings: AutopilotSettings):
        """保存本地配置"""
        with open(self.local_config_path, "w") as f:
            yaml.dump(settings.to_dict(), f, default_flow_style=False)
        print(f"✅ 本地配置已保存到 {self.local_config_path}")

    def init_project_config(self, force: bool = False):
        """初始化项目配置"""
        if self.project_config_path.exists() and not force:
            print(f"⚠️  项目配置已存在: {self.project_config_path}")
            return False

        settings = AutopilotSettings()
        self.save_project(settings)

        # 创建必要的目录
        (self.project_root / ".autopilot").mkdir(exist_ok=True)
        (self.project_root / ".autopilot" / "skills").mkdir(exist_ok=True)

        # 创建 .gitignore
        gitignore = self.project_root / ".gitignore"
        if gitignore.exists():
            with open(gitignore) as f:
                content = f.read()
            if ".autopilot/" not in content:
                with open(gitignore, "a") as f:
                    f.write("\n# autopilot\n.autopilot/\n")
                print(f"✅ 已添加 .autopilot/ 到 .gitignore")

        return True


def load_config(project_root: Optional[Path] = None) -> AutopilotSettings:
    """加载配置的便捷函数"""
    loader = ConfigLoader(project_root)
    return loader.load()


def load_workflow(workflow_name: str, project_root: Optional[Path] = None) -> Optional[WorkflowDefinition]:
    """根据名称加载工作流定义"""
    settings = load_config(project_root)
    for workflow in settings.workflows:
        if workflow.name == workflow_name:
            return workflow
    return None


# CLI 入口
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Autopilot 配置管理")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # show - 显示配置
    show_parser = subparsers.add_parser("show", help="显示当前配置")
    show_parser.add_argument("--project-root", "-p", type=Path, default=Path.cwd(), help="项目根目录")

    # init - 初始化项目配置
    init_parser = subparsers.add_parser("init", help="初始化项目配置")
    init_parser.add_argument("--project-root", "-p", type=Path, default=Path.cwd(), help="项目根目录")
    init_parser.add_argument("--force", "-f", action="store_true", help="强制覆盖")

    # set - 设置配置
    set_parser = subparsers.add_parser("set", help="设置配置值")
    set_parser.add_argument("key", help="配置键 (如: learning.enabled)")
    set_parser.add_argument("value", help="配置值")
    set_parser.add_argument("--project-root", "-p", type=Path, default=Path.cwd(), help="项目根目录")
    set_parser.add_argument("--local", "-l", action="store_true", help="保存到本地配置")

    args = parser.parse_args()

    if args.command == "show" or args.command is None:
        loader = ConfigLoader(args.project_root)
        settings = loader.load()

        print(f"\n📋 Autopilot 配置")
        print(f"{'='*60}")
        print(f"   全局配置: {loader.global_config_path} ({'存在' if loader.global_config_path.exists() else '不存在'})")
        print(f"   项目配置: {loader.project_config_path} ({'存在' if loader.project_config_path.exists() else '不存在'})")
        print(f"   本地配置: {loader.local_config_path} ({'存在' if loader.local_config_path.exists() else '不存在'})")
        print(f"{'='*60}\n")

        def print_dict(d, indent=0):
            for key, value in d.items():
                if isinstance(value, dict):
                    print(f"{'  ' * indent}📁 {key}:")
                    print_dict(value, indent + 1)
                else:
                    print(f"{'  ' * indent}• {key}: {value}")

        print_dict(settings.to_dict())

    elif args.command == "init":
        loader = ConfigLoader(args.project_root)
        if loader.init_project_config(force=args.force):
            print(f"✅ 项目配置初始化完成")

    elif args.command == "set":
        loader = ConfigLoader(args.project_root)
        settings = loader.load()

        # 转换值类型
        value = args.value
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.isdigit():
            value = int(value)

        # 设置配置
        keys = args.key.split(".")
        config_dict = settings.to_dict()
        current = config_dict
        for k in keys[:-1]:
            current = current.setdefault(k, {})
        current[keys[-1]] = value

        settings = AutopilotSettings.from_dict(config_dict)

        if args.local:
            loader.save_local(settings)
        else:
            loader.save_project(settings)