"""
MCP 客户端模块：通过 Higress 网关调用钉钉差旅 MCP 工具。

职责：
    封装对 MCP（Model Context Protocol）服务的调用，对外提供统一的工具调用接口。

设计思路：
    - 支持两种运行模式：
      1. 生产模式：通过 HTTP JSON-RPC 调用 Higress MCP endpoint。
      2. Mock 模式：本地模拟返回，用于开发和演示（无需配置 mcp_auth_token）。
    - 生产模式下使用 tenacity 实现自动重试（最多 3 次，指数退避）。
    - 支持 list_tools 获取可用工具列表。

与其他模块的关系：
    - 被所有需要调用后端服务的 Agent 和 Skill 使用。
    - 依赖 config 读取 MCP endpoint 和认证令牌。
    - Mock 模式依赖 mcp/tools/mock_data 提供模拟数据。
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings


class MCPClient:
    """MCP 工具调用客户端，自动根据环境选择远程调用或本地 Mock。

    Attributes:
        endpoint: MCP 网关端点地址。
        auth_token: 认证令牌。
    """

    def __init__(self):
        settings = get_settings()
        self.endpoint = settings.mcp_endpoint
        self.auth_token = settings.mcp_auth_token
        # 开发环境且未配置 auth_token 时自动切换为 Mock 模式
        self._use_mock = settings.app_env == "development" and not settings.mcp_auth_token
        if self._use_mock:
            logger.debug("[MCPClient] 使用 Mock 模式")

    async def call_tool(self, tool_name: str, params: dict[str, Any]) -> Any:
        """调用 MCP 工具，开发环境自动降级为 Mock。

        Args:
            tool_name: 工具名称（如 travel_apply、get_hotel_list 等）。
            params: 工具调用参数。

        Returns:
            Any: 工具执行结果。
        """
        if self._use_mock:
            logger.debug(f"[MCPClient] Mock 调用: {tool_name}, params={params}")
            return await self._mock_call(tool_name, params)

        return await self._remote_call(tool_name, params)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _remote_call(self, tool_name: str, params: dict[str, Any]) -> Any:
        """通过 Higress MCP endpoint 远程调用工具（带自动重试）。

        Args:
            tool_name: 工具名称。
            params: 工具调用参数。

        Returns:
            Any: JSON-RPC 返回的 result 字段。

        Raises:
            MCPError: MCP 返回错误信息时抛出。
            httpx.HTTPStatusError: HTTP 请求失败时抛出。
        """
        logger.info(f"[MCPClient] 远程调用: {tool_name}")
        t0 = time.time()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self.endpoint,
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": params},
                    "id": 1,
                },
                headers={
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                raise MCPError(data["error"].get("message", "Unknown MCP error"))

            elapsed = time.time() - t0
            logger.info(f"[MCPClient] 远程调用完成: {tool_name}, 耗时={elapsed:.2f}s")
            return data.get("result", {})

    async def _mock_call(self, tool_name: str, params: dict[str, Any]) -> Any:
        """Mock 调用，返回本地模拟数据。

        Args:
            tool_name: 工具名称。
            params: 工具调用参数。

        Returns:
            Any: 模拟的返回数据。
        """
        from app.mcp.tools.mock_data import get_mock_response
        return get_mock_response(tool_name, params)

    async def list_tools(self) -> list[dict]:
        """获取 MCP 可用工具列表。

        Returns:
            list[dict]: 工具定义列表，每项包含 name 和 description。
        """
        if self._use_mock:
            logger.debug("[MCPClient] 返回 Mock 工具列表")
            return _MOCK_TOOLS

        logger.info("[MCPClient] 获取远程工具列表")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                self.endpoint,
                json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                headers={"Authorization": f"Bearer {self.auth_token}"},
            )
            resp.raise_for_status()
            return resp.json().get("result", {}).get("tools", [])


class MCPError(Exception):
    """MCP 服务端返回错误时抛出的异常。"""
    pass


_MOCK_TOOLS = [
    {"name": "travel_apply", "description": "提交出差申请"},
    {"name": "travel_apply_status", "description": "查询出差申请状态"},
    {"name": "get_hotel_list", "description": "获取酒店列表"},
    {"name": "get_hotel_detail", "description": "获取酒店详情"},
    {"name": "get_flights", "description": "获取机票列表"},
    {"name": "get_trains", "description": "获取高铁票列表"},
    {"name": "book_hotel", "description": "预订酒店"},
    {"name": "book_flight", "description": "预订机票"},
    {"name": "book_train", "description": "预订高铁票"},
]
