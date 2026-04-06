"""Config - Pydantic 配置类

与 config.yaml 结构完全映射，支持环境变量替换
"""

import os
import re
from pathlib import Path
from typing import Any, List, Optional

import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 配置文件路径
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.yaml"

# 环境变量引用正则: ${VAR_NAME} 或 ${VAR_NAME:-default}
ENV_VAR_PATTERN = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}')


def _replace_env_vars(value: Any) -> Any:
    """递归替换值中的环境变量引用"""
    if isinstance(value, str):
        def replace_var(match):
            var_name = match.group(1)
            default_val = match.group(2)
            return os.getenv(var_name, default_val if default_val is not None else "")
        result = ENV_VAR_PATTERN.sub(replace_var, value)
        # 将 "null" 字符串转换为 None（用于可选整数如 max_rounds）
        if result == "null":
            return None
        return result
    elif isinstance(value, dict):
        return {k: _replace_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_replace_env_vars(item) for item in value]
    return value


# ==================== Pydantic 模型定义 ====================

class AppConfig(BaseModel):
    """应用基础配置"""
    name: str = "Learn Claude Code API"
    version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"


class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8001


def _get_db_host() -> str:
    """获取数据库 host，支持环境变量"""
    return os.getenv("DB_HOST", "host.docker.internal")


def _get_db_name() -> str:
    """获取数据库名，支持环境变量"""
    return os.getenv("DB_NAME", "agent_memory")


def _get_db_user() -> str:
    """获取数据库用户，支持环境变量"""
    return os.getenv("DB_USER", "postgres")


def _get_db_password() -> str:
    """获取数据库密码，支持环境变量"""
    return os.getenv("DB_PASSWORD", "123456")


class DatabaseConfig(BaseModel):
    """数据库配置"""
    driver: str = "postgresql+asyncpg"
    host: str = Field(default_factory=_get_db_host)
    port: int = 5432
    name: str = Field(default_factory=_get_db_name)
    user: str = Field(default_factory=_get_db_user)
    password: str = Field(default_factory=_get_db_password)
    pool_size: int = 10
    max_overflow: int = 20

    @property
    def url(self) -> str:
        """生成数据库连接URL"""
        return f"{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class JWTConfig(BaseModel):
    """JWT 配置"""
    secret_key: str = "default-secret-key"
    algorithm: str = "HS256"
    expire_minutes: int = 1440


class ApiKeysConfig(BaseModel):
    """API 密钥配置"""
    deepseek: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    anthropic: str = ""
    anthropic_base_url: str = ""
    openai: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    moonshot: str = ""
    moonshot_base_url: str = "https://api.moonshot.cn/v1"
    kimi: str = ""


class ModelConfig(BaseModel):
    """模型配置"""
    id: str = "deepseek/deepseek-reasoner"
    default: str = "deepseek/deepseek-reasoner"


class AgentConfig(BaseModel):
    """Agent 配置"""
    type: str = "deep"
    max_rounds: Optional[int] = None
    recursion_limit: int = 100


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    json_enabled: bool = Field(default=False, alias="json")
    file: str = "logs/app.log"
    rotation: str = "10 MB"
    retention: str = "7 days"
    deep_dir: str = "logs/deep"
    deep_rotation: str = "100 MB"
    deep_retention: str = "3 days"


class TodoConfig(BaseModel):
    """Todo 配置"""
    max_items: int = 20
    reminder_rounds: int = 3
    enable_hook: bool = True


class SkillEditConfig(BaseModel):
    """Skill Edit 配置"""
    enable_hitl: bool = True


class SecurityConfig(BaseModel):
    """安全配置"""
    blacklist_commands: List[str] = Field(default_factory=list)
    blacklist_paths: List[str] = Field(default_factory=list)
    whitelist_commands: List[str] = Field(default_factory=list)


class SandboxConfig(BaseModel):
    """Sandbox 配置"""
    mode: str = "docker"


class ConfigSchema(BaseModel):
    """配置 Schema - 与 config.yaml 结构完全映射"""
    app: AppConfig = Field(default_factory=AppConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    jwt: JWTConfig = Field(default_factory=JWTConfig)
    api_keys: ApiKeysConfig = Field(default_factory=ApiKeysConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    todo: TodoConfig = Field(default_factory=TodoConfig)
    skill_edit: SkillEditConfig = Field(default_factory=SkillEditConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)


# ==================== 配置加载器 ====================

class Config:
    """统一配置管理器

    所有后端代码都通过此类访问配置：
        from backend.infrastructure.config import config

        db_url = config.database.url
        jwt_secret = config.jwt.secret_key
    """

    _instance = None
    _config: ConfigSchema = ConfigSchema()  # 默认初始化避免 None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载配置文件并解析为 Pydantic 模型"""
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f) or {}
                # 替换环境变量
                processed_config = _replace_env_vars(raw_config)
                self._config = ConfigSchema.model_validate(processed_config)
        else:
            self._config = ConfigSchema()

    # 属性代理到 Pydantic 模型
    @property
    def app(self) -> AppConfig:
        return self._config.app

    @property
    def server(self) -> ServerConfig:
        return self._config.server

    @property
    def database(self) -> DatabaseConfig:
        return self._config.database

    @property
    def jwt(self) -> JWTConfig:
        return self._config.jwt

    @property
    def api_keys(self) -> ApiKeysConfig:
        return self._config.api_keys

    @property
    def model(self) -> ModelConfig:
        return self._config.model

    @property
    def agent(self) -> AgentConfig:
        return self._config.agent

    @property
    def logging(self) -> LoggingConfig:
        return self._config.logging

    @property
    def todo(self) -> TodoConfig:
        return self._config.todo

    @property
    def skill_edit(self) -> SkillEditConfig:
        return self._config.skill_edit

    @property
    def security(self) -> SecurityConfig:
        return self._config.security

    @property
    def sandbox(self) -> SandboxConfig:
        return self._config.sandbox


# 全局配置实例
config = Config()


def get_database_url() -> str:
    """获取数据库连接 URL

    用于 backward compatibility。
    新代码应直接使用 config.database.url
    """
    return config.database.url
