"""
Memory 管理器模块：短期记忆（对话）+ 长期记忆（用户偏好）+ 工作记忆（任务状态）。

职责：
    统一管理三层记忆体系，为 Agent 提供上下文感知能力。

设计思路（参照 Manus/OpenClaw 的 Memory 机制）：
    - 短期记忆：当前会话的对话历史，内存存储（生产环境可迁移至 Redis）。
    - 长期记忆：用户偏好和历史出差记录（生产环境可持久化到 PostgreSQL）。
    - 工作记忆：当前任务的中间状态，随会话生命周期存在。
    - 短期记忆设有 50 条上限，自动滑窗淘汰旧消息。

与其他模块的关系：
    - 被 orchestrator / context_manager 调用，构建上下文摘要。
    - 被 api/chat 调用，保存和读取对话消息。
    - 单例模式，通过 get_memory_manager() 获取。
"""

from __future__ import annotations

from typing import Any
from datetime import datetime
from loguru import logger

from app.config import get_settings


class MemoryManager:
    """统一的三层记忆管理器。

    Attributes:
        _short_term: 短期记忆存储，key 为 session_id。
        _long_term: 长期记忆存储，key 为 user_id。
        _working: 工作记忆存储，key 为 session_id。
    """

    def __init__(self):
        self._short_term: dict[str, list[dict]] = {}
        self._long_term: dict[str, dict[str, Any]] = {}
        self._working: dict[str, dict[str, Any]] = {}
        logger.debug("[MemoryManager] 初始化完成")

    async def save_short_term(
        self, session_id: str, role: str, content: str, metadata: dict | None = None
    ) -> None:
        """保存短期记忆（对话消息）。

        Args:
            session_id: 会话 ID。
            role: 消息角色（user / assistant）。
            content: 消息内容。
            metadata: 附加元数据（可选）。
        """
        if session_id not in self._short_term:
            self._short_term[session_id] = []

        self._short_term[session_id].append({
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        })

        # 滑窗淘汰：保留最近 50 条消息
        max_messages = 50
        if len(self._short_term[session_id]) > max_messages:
            self._short_term[session_id] = self._short_term[session_id][-max_messages:]

        logger.debug(f"[MemoryManager] 短期记忆已保存, session={session_id}, role={role}")

    async def get_short_term(
        self, session_id: str, limit: int = 20
    ) -> list[dict]:
        """获取短期记忆（最近的对话消息）。

        Args:
            session_id: 会话 ID。
            limit: 最多返回的消息条数。

        Returns:
            list[dict]: 最近的消息列表。
        """
        messages = self._short_term.get(session_id, [])
        return messages[-limit:]

    async def save_long_term(
        self, user_id: str, key: str, value: Any
    ) -> None:
        """保存长期记忆（用户偏好等）。

        Args:
            user_id: 用户 ID。
            key: 记忆键名。
            value: 记忆值。
        """
        if user_id not in self._long_term:
            self._long_term[user_id] = {}
        self._long_term[user_id][key] = {
            "value": value,
            "updated_at": datetime.now().isoformat(),
        }
        logger.debug(f"[MemoryManager] 长期记忆已保存: user={user_id}, key={key}")

    async def get_long_term(self, user_id: str, key: str) -> Any | None:
        """获取长期记忆。

        Args:
            user_id: 用户 ID。
            key: 记忆键名。

        Returns:
            Any | None: 记忆值，不存在时返回 None。
        """
        user_data = self._long_term.get(user_id, {})
        entry = user_data.get(key)
        return entry["value"] if entry else None

    async def get_user_preferences(self, user_id: str) -> dict[str, Any]:
        """获取用户的差旅偏好集合。

        Args:
            user_id: 用户 ID。

        Returns:
            dict: 以偏好名为键的偏好字典。
        """
        prefs = {}
        user_data = self._long_term.get(user_id, {})
        for key in ["preferred_hotel_brand", "preferred_airline", "seat_preference",
                     "budget_level", "frequent_destinations"]:
            entry = user_data.get(key)
            if entry:
                prefs[key] = entry["value"]
        return prefs

    async def update_working_memory(
        self, session_id: str, key: str, value: Any
    ) -> None:
        """更新工作记忆（当前任务中间状态）。

        Args:
            session_id: 会话 ID。
            key: 状态键名。
            value: 状态值。
        """
        if session_id not in self._working:
            self._working[session_id] = {}
        self._working[session_id][key] = value

    async def get_working_memory(self, session_id: str) -> dict[str, Any]:
        """获取当前会话的工作记忆。

        Args:
            session_id: 会话 ID。

        Returns:
            dict: 工作记忆字典，不存在时返回空字典。
        """
        return self._working.get(session_id, {})

    async def clear_working_memory(self, session_id: str) -> None:
        """清除指定会话的工作记忆。

        Args:
            session_id: 会话 ID。
        """
        self._working.pop(session_id, None)
        logger.debug(f"[MemoryManager] 工作记忆已清除, session={session_id}")

    async def build_context_summary(self, session_id: str, user_id: str) -> str:
        """构建上下文摘要，供 Orchestrator 和 Prompt 引擎使用。

        Args:
            session_id: 会话 ID。
            user_id: 用户 ID。

        Returns:
            str: 拼接好的上下文摘要文本。
        """
        parts = []

        preferences = await self.get_user_preferences(user_id)
        if preferences:
            parts.append(f"用户偏好: {preferences}")

        working = await self.get_working_memory(session_id)
        if working:
            parts.append(f"当前任务状态: {working}")

        recent = await self.get_short_term(session_id, limit=3)
        if recent:
            recent_summary = "; ".join(
                f"{m['role']}: {m['content'][:50]}" for m in recent
            )
            parts.append(f"最近对话: {recent_summary}")

        return "\n".join(parts) if parts else "暂无上下文信息"


_memory_instance: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    """获取 MemoryManager 全局单例。

    Returns:
        MemoryManager: 全局单例实例。
    """
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = MemoryManager()
        logger.info("[MemoryManager] 全局单例创建完成")
    return _memory_instance
