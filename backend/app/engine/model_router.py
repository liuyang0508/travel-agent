"""
模型路由器模块：根据任务类型将请求分发到不同的 LLM 提供商。

职责：
    封装 LLM 实例的创建和缓存，对外提供按用途区分的模型获取接口。

设计思路：
    - 通过 provider 参数区分模型提供商（glm / qwen）。
    - 使用 _model_cache 缓存已创建的实例，避免重复初始化。
    - 不同用途使用不同的 temperature：意图识别 0.1（确定性高）、
      规划 0.2（略有创意）、对话 0.7（更自然）。

与其他模块的关系：
    - 被所有 Agent 调用，获取对应任务的 LLM 实例。
    - 依赖 config 模块读取 API Key、模型名称和默认提供商配置。
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from loguru import logger

from app.config import get_settings

_model_cache: dict[str, ChatOpenAI] = {}


def get_llm(provider: str | None = None, temperature: float = 0.3) -> ChatOpenAI:
    """获取 LLM 实例（带缓存）。

    Args:
        provider: 模型提供商，"glm" 或 "qwen"。为 None 时使用默认 chat 模型。
        temperature: 生成温度，影响输出随机性。

    Returns:
        ChatOpenAI: LangChain ChatOpenAI 兼容的 LLM 实例。

    Raises:
        ValueError: 指定了未知的 provider。
    """
    settings = get_settings()
    provider = provider or settings.default_chat_model

    cache_key = f"{provider}_{temperature}"
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    logger.info(f"[ModelRouter] 创建 LLM 实例: provider={provider}, temperature={temperature}")

    if provider == "glm":
        llm = ChatOpenAI(
            model=settings.glm_model,
            api_key=settings.glm_api_key,
            base_url=settings.glm_base_url,
            temperature=temperature,
        )
    elif provider == "qwen":
        llm = ChatOpenAI(
            model=settings.qwen_model,
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url,
            temperature=temperature,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

    _model_cache[cache_key] = llm
    return llm


def get_intent_llm() -> ChatOpenAI:
    """获取意图识别专用 LLM（低 temperature，确定性高）。

    Returns:
        ChatOpenAI: 配置为 temperature=0.1 的 LLM 实例。
    """
    settings = get_settings()
    return get_llm(settings.default_intent_model, temperature=0.1)


def get_planning_llm() -> ChatOpenAI:
    """获取任务规划专用 LLM（中等 temperature，兼顾准确和创意）。

    Returns:
        ChatOpenAI: 配置为 temperature=0.2 的 LLM 实例。
    """
    settings = get_settings()
    return get_llm(settings.default_planning_model, temperature=0.2)


def get_chat_llm() -> ChatOpenAI:
    """获取对话生成专用 LLM（高 temperature，输出更自然）。

    Returns:
        ChatOpenAI: 配置为 temperature=0.7 的 LLM 实例。
    """
    settings = get_settings()
    return get_llm(settings.default_chat_model, temperature=0.7)
