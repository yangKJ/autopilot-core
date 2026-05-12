#!/usr/bin/env python3
"""
Autopilot MCP Server
提供 autopilot_* 工具给 Claude Code 使用
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# 尝试导入 MCP SDK
try:
    from mcp.server import Server
    from mcp.types import Tool, ToolInputSchema
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


# MCP Server 名
SERVER_NAME = "autopilot"
SERVER_VERSION = "0.1.0"


class AutopilotMCPServer:
    """Autopilot MCP Server"""

    def __init__(self):
        self.tools = self._register_tools()

    def _register_tools(self) -> List[Tool]:
        """注册所有 MCP 工具"""
        tools = [
            Tool(
                name="autopilot_run",
                description="运行自动驾驶模式，处理变更文件",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "要处理的文件列表"
                        },
                        "dry_run": {
                            "type": "boolean",
                            "description": "干跑模式，不实际执行"
                        }
                    }
                }
            ),
            Tool(
                name="autopilot_predict",
                description="预测文件执行成功率",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "要预测的文件列表"
                        }
                    }
                }
            ),
            Tool(
                name="autopilot_trend",
                description="获取执行趋势分析",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chain": {
                            "type": "string",
                            "description": "链条名称（可选）"
                        },
                        "days": {
                            "type": "integer",
                            "description": "分析天数（默认7）"
                        }
                    }
                }
            ),
            Tool(
                name="autopilot_health",
                description="检查项目健康状态",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="autopilot_config",
                description="获取或设置配置",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["get", "set"],
                            "description": "操作类型"
                        },
                        "key": {
                            "type": "string",
                            "description": "配置键"
                        },
                        "value": {
                            "type": "any",
                            "description": "配置值（set时使用）"
                        }
                    }
                }
            ),
        ]
        return tools

    def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用"""
        if tool_name == "autopilot_run":
            return self._tool_autopilot_run(arguments)
        elif tool_name == "autopilot_predict":
            return self._tool_autopilot_predict(arguments)
        elif tool_name == "autopilot_trend":
            return self._tool_autopilot_trend(arguments)
        elif tool_name == "autopilot_health":
            return self._tool_autopilot_health(arguments)
        elif tool_name == "autopilot_config":
            return self._tool_autopilot_config(arguments)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _tool_autopilot_run(self, args: Dict) -> Dict[str, Any]:
        """运行自动驾驶"""
        try:
            from ..core.autonomous import AutonomousScheduler, AutopilotConfig

            files = args.get("files")
            dry_run = args.get("dry_run", False)

            config = AutopilotConfig(project_root=Path.cwd())
            scheduler = AutonomousScheduler(config=config, dry_run=dry_run)

            success = scheduler.run_full_cycle(files=files)

            return {
                "success": success,
                "message": "自动驾驶完成" if success else "自动驾驶失败"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_autopilot_predict(self, args: Dict) -> Dict[str, Any]:
        """预测成功率"""
        try:
            from ..core.learning_engine import predict_failure_risk

            files = args.get("files", [])
            if not files:
                return {"success": False, "error": "需要提供文件列表"}

            result = predict_failure_risk(files)
            return {
                "success": True,
                "prediction": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_autopilot_trend(self, args: Dict) -> Dict[str, Any]:
        """获取趋势"""
        try:
            from ..core.learning_engine import get_trend_analysis

            chain = args.get("chain")
            days = args.get("days", 7)

            result = get_trend_analysis(chain_name=chain, days=days)
            return {
                "success": True,
                "trend": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_autopilot_health(self, args: Dict) -> Dict[str, Any]:
        """健康检查"""
        try:
            from ..core.config import ConfigLoader

            loader = ConfigLoader()
            settings = loader.load()

            project_root = Path.cwd()
            config_exists = (project_root / ".autopilot.yaml").exists()

            return {
                "success": True,
                "health": {
                    "configured": config_exists,
                    "learning_enabled": settings.learning_enabled
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_autopilot_config(self, args: Dict) -> Dict[str, Any]:
        """配置操作"""
        try:
            from ..core.config import ConfigLoader, AutopilotSettings

            action = args.get("action", "get")

            loader = ConfigLoader()
            settings = loader.load()

            if action == "get":
                return {
                    "success": True,
                    "config": settings.to_dict()
                }
            elif action == "set":
                key = args.get("key")
                value = args.get("value")

                if not key:
                    return {"success": False, "error": "需要提供配置键"}

                keys = key.split(".")
                config_dict = settings.to_dict()
                current = config_dict
                for k in keys[:-1]:
                    current = current.setdefault(k, {})
                current[keys[-1]] = value

                settings = AutopilotSettings.from_dict(config_dict)
                loader.save_project(settings)

                return {
                    "success": True,
                    "message": f"已设置 {key} = {value}"
                }

            return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


def create_mcp_server() -> Optional[Server]:
    """创建 MCP Server（如果 MCP SDK 可用）"""
    if not HAS_MCP:
        return None

    server = Server(name=SERVER_NAME, version=SERVER_VERSION)
    autopilot = AutopilotMCPServer()

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return autopilot.tools

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return autopilot.handle_tool_call(name, arguments)

    return server


# 简单 HTTP 服务器模式（无 MCP SDK 时）
class SimpleMCPServer:
    """简单 MCP Server（基于 JSON-RPC over HTTP）"""

    def __init__(self, port: int = 8766):
        self.port = port
        self.autopilot = AutopilotMCPServer()

    def handle_request(self, request: Dict) -> Dict:
        """处理 JSON-RPC 请求"""
        method = request.get("method", "")
        params = request.get("params", {})

        if method == "tools/list":
            return {"result": self.autopilot.tools}
        elif method.startswith("tools/"):
            tool_name = method.replace("tools/", "")
            return {"result": self.autopilot.handle_tool_call(tool_name, params)}
        else:
            return {"error": {"code": -32601, "message": "Method not found"}}

    def run(self):
        """运行服务器"""
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import json

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length)
                request = json.loads(body)
                response = self.server.server.handle_request(request)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())

            def log_message(self, format, *args):
                pass  # 静默日志

        server = HTTPServer(("localhost", self.port), Handler)
        print(f"🤖 Autopilot MCP Server 运行在 http://localhost:{self.port}")
        print(f"   使用 MCP 客户端连接")
        server.serve_forever()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Autopilot MCP Server")
    parser.add_argument("--port", "-p", type=int, default=8766, help="端口号")
    parser.add_argument("--mcp", action="store_true", help="使用 MCP 协议模式")

    args = parser.parse_args()

    if args.mcp and HAS_MCP:
        server = create_mcp_server()
        if server:
            print(f"🤖 Autopilot MCP Server ({SERVER_NAME} v{SERVER_VERSION})")
            # 运行 MCP 服务器
            # server.run()
    else:
        # 简单模式
        simple = SimpleMCPServer(port=args.port)
        simple.run()


if __name__ == "__main__":
    main()