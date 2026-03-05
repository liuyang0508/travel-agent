"""
上下文治理器模块：管理 Token 预算、上下文窗口压缩和信息筛选。

职责：
    控制送入 LLM 的上下文大小，在信息量和 Token 成本之间取得平衡。

设计思路（参照 Cursor / Claude Code 的 Context 管理策略）：
    - Token 预算控制：每个会话最大 8000 token，超过阈值自动触发压缩。
    - 上下文自动压缩：保留最近消息 + 将早期消息提炼为摘要。
    - 相关性排序：基于关键词重叠度和时间新鲜度评分，优先保留相关上下文。
    - 懒加载：按需加载上下文，不一次性灌入所有信息。

与其他模块的关系：
    - 被 orchestrator 在构建 LLM 输入时调用，控制上下文窗口大小。
    - 被 memory_manager 配合使用，共同管理会话上下文。
"""

from __future__ import annotations

from typing import Any
from loguru import logger


class ContextManager:
    """上下文治理器，负责 Token 预算控制、上下文压缩和相关性筛选。

    Attributes:
        MAX_CONTEXT_TOKENS: 单会话最大 Token 预算。
        COMPACT_THRESHOLD: 触发压缩的使用率阈值（0.0~1.0）。
    """

    MAX_CONTEXT_TOKENS = 8000
    COMPACT_THRESHOLD = 0.8

    def __init__(self):
        self._token_usage: dict[str, int] = {}

    def estimate_tokens(self, text: str) -> int:
        """粗略估算文本的 Token 数量。

        Args:
            text: 待估算的文本。

        Returns:
            int: 预估的 Token 数（中文约 1 字 ≈ 1.5 token，英文约 4 字符 ≈ 1 token）。
        """
        cn_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        en_chars = len(text) - cn_chars
        return int(cn_chars * 1.5 + en_chars * 0.25)

    def should_compact(self, session_id: str) -> bool:
        """判断指定会话是否需要压缩上下文。

        Args:
            session_id: 会话 ID。

        Returns:
            bool: Token 使用量超过阈值时返回 True。
        """
        usage = self._token_usage.get(session_id, 0)
        threshold = self.MAX_CONTEXT_TOKENS * self.COMPACT_THRESHOLD
        need = usage > threshold
        if need:
            logger.info(f"[ContextManager] 会话 {session_id} 需要压缩, "
                        f"当前用量={usage}, 阈值={threshold:.0f}")
        return need

    async def compact_context(
        self, messages: list[dict], keep_recent: int = 6
    ) -> list[dict]:
        """压缩上下文：保留最近消息，将早期内容摘要化。

        Args:
            messages: 完整的消息列表。
            keep_recent: 保留最近的消息条数。

        Returns:
            list[dict]: 压缩后的消息列表（摘要 + 最近消息）。
        """
        if len(messages) <= keep_recent:
            return messages

        early_messages = messages[:-keep_recent]
        recent_messages = messages[-keep_recent:]

        summary = self._summarize_messages(early_messages)
        compacted = [{"role": "system", "content": f"[历史摘要] {summary}"}]
        compacted.extend(recent_messages)

        logger.info(f"[ContextManager] 上下文压缩完成: {len(messages)} 条 → {len(compacted)} 条, "
                    f"节省约 {len(early_messages)} 条消息")
        return compacted

    def _summarize_messages(self, messages: list[dict]) -> str:
        """从消息列表中提取差旅相关的关键信息作为摘要。

        Args:
            messages: 早期消息列表。

        Returns:
            str: 关键信息摘要文本。
        """
        key_info = []
        for msg in messages:
            content = msg.get("content", "")
            if any(kw in content for kw in ["目的地", "出发", "日期", "申请", "审批", "酒店", "机票"]):
                key_info.append(content[:80])

        if not key_info:
            return f"共 {len(messages)} 轮对话"
        return " | ".join(key_info[:5])

    def select_relevant_context(
        self, query: str, candidates: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """基于相关性评分选择最相关的上下文片段。

        Args:
            query: 当前用户查询。
            candidates: 候选上下文片段列表。
            top_k: 返回的最大条目数。

        Returns:
            list[dict]: 按相关性降序排列的 top_k 条上下文。
        """
        scored = []
        query_keywords = set(query)

        for item in candidates:
            content = str(item.get("content", ""))
            # 基于字符级关键词重叠度 + 时间新鲜度加分
            overlap = len(query_keywords & set(content))
            recency_bonus = item.get("recency_score", 0)
            score = overlap + recency_bonus
            scored.append((score, item))

        scored.sort(key=lambda x: -x[0])
        return [item for _, item in scored[:top_k]]

    def track_usage(self, session_id: str, text: str) -> dict[str, int]:
        """跟踪并累加会话的 Token 使用量。

        Args:
            session_id: 会话 ID。
            text: 新增文本。

        Returns:
            dict: 包含 session_tokens、max_tokens、usage_pct 的使用统计。
        """
        tokens = self.estimate_tokens(text)
        self._token_usage[session_id] = self._token_usage.get(session_id, 0) + tokens
        usage = {
            "session_tokens": self._token_usage[session_id],
            "max_tokens": self.MAX_CONTEXT_TOKENS,
            "usage_pct": self._token_usage[session_id] / self.MAX_CONTEXT_TOKENS,
        }
        logger.debug(f"[ContextManager] Token 用量: session={session_id}, "
                     f"已用={usage['session_tokens']}, 比例={usage['usage_pct']:.1%}")
        return usage

    def reset_usage(self, session_id: str) -> None:
        """重置指定会话的 Token 用量计数。

        Args:
            session_id: 会话 ID。
        """
        self._token_usage.pop(session_id, None)
        logger.debug(f"[ContextManager] Token 用量已重置, session={session_id}")
