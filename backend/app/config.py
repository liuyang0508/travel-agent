"""
应用配置管理模块。

职责：
    集中管理所有运行时配置项，支持从环境变量和 .env 文件加载。

核心概念：
    - 使用 pydantic-settings 实现类型安全的配置解析与校验。
    - 通过 lru_cache 保证全局单例，避免重复读取环境变量。
    - 配置项分组：应用基础、LLM 模型、MCP 网关、PostgreSQL、Redis。

与其他模块的关系：
    - 被 main.py 在启动时读取环境信息。
    - 被 model_router 读取 LLM API Key 和模型名称。
    - 被 mcp/client 读取 MCP 网关地址和认证令牌。
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from loguru import logger


class Settings(BaseSettings):
    """应用全局配置，自动从环境变量 / .env 文件加载。

    Attributes:
        app_env: 运行环境（development / staging / production）
        app_debug: 是否启用调试模式
        app_secret_key: 应用密钥，用于签名等场景
        glm_api_key: 智谱 GLM 模型 API Key
        glm_base_url: 智谱 API 基础地址
        glm_model: 默认 GLM 模型名称
        qwen_api_key: 通义千问 API Key
        qwen_base_url: 通义千问 API 基础地址
        qwen_model: 默认千问模型名称
        default_intent_model: 意图识别默认使用的模型提供商
        default_planning_model: 任务规划默认使用的模型提供商
        default_chat_model: 对话生成默认使用的模型提供商
        mcp_endpoint: MCP 网关端点地址
        mcp_auth_token: MCP 认证令牌
        postgres_host: PostgreSQL 主机
        postgres_port: PostgreSQL 端口
        postgres_db: PostgreSQL 数据库名
        postgres_user: PostgreSQL 用户名
        postgres_password: PostgreSQL 密码
        redis_host: Redis 主机
        redis_port: Redis 端口
        redis_password: Redis 密码
    """

    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me-in-production"

    glm_api_key: str = ""
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    glm_model: str = "glm-4"

    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-plus"

    default_intent_model: str = "qwen"
    default_planning_model: str = "glm"
    default_chat_model: str = "qwen"

    mcp_endpoint: str = "http://higress-gateway:8080/mcp"
    mcp_auth_token: str = ""

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "travel_agent"
    postgres_user: str = "travel"
    postgres_password: str = "travel_secret"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    @property
    def database_url(self) -> str:
        """构建 PostgreSQL 异步连接 URL。

        Returns:
            str: asyncpg 格式的数据库连接字符串。
        """
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """构建 Redis 连接 URL。

        Returns:
            str: redis:// 格式的连接字符串，含可选认证信息。
        """
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例（首次调用后缓存）。

    Returns:
        Settings: 已加载环境变量的配置实例。
    """
    settings = Settings()
    logger.info(f"[Config] 配置加载完成, 环境={settings.app_env}, "
                f"意图模型={settings.default_intent_model}, "
                f"规划模型={settings.default_planning_model}")
    return settings
