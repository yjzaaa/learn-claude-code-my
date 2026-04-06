"""
Privacy Configuration - 隐私配置模型

定义记忆系统的隐私配置，支持多种存储模式、同步策略和敏感信息过滤。
"""

import re
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PrivacyMode(StrEnum):
    """隐私模式 - 控制记忆数据的存储位置"""

    SERVER = "server"  # 完全存储在服务器
    LOCAL = "local"  # 仅本地存储
    HYBRID = "hybrid"  # 混合模式（敏感信息本地，其他服务器）


class SyncStrategy(StrEnum):
    """同步策略 - 控制本地与服务器数据的同步方式"""

    REALTIME = "realtime"  # 实时同步
    PERIODIC = "periodic"  # 定期同步
    MANUAL = "manual"  # 手动同步


class TypePrivacySettings(BaseModel):
    """
    记忆类型隐私设置

    为每种记忆类型指定隐私模式，可覆盖全局设置。
    """

    user: PrivacyMode = Field(default=PrivacyMode.SERVER, description="用户记忆的隐私模式")
    feedback: PrivacyMode = Field(default=PrivacyMode.SERVER, description="反馈记忆的隐私模式")
    project: PrivacyMode = Field(default=PrivacyMode.SERVER, description="项目记忆的隐私模式")
    reference: PrivacyMode = Field(default=PrivacyMode.SERVER, description="引用记忆的隐私模式")

    def to_dict(self) -> dict[str, PrivacyMode]:
        """转换为字典格式"""
        return {
            "user": self.user,
            "feedback": self.feedback,
            "project": self.project,
            "reference": self.reference,
        }

    @classmethod
    def from_dict(cls, data: dict[str, PrivacyMode]) -> "TypePrivacySettings":
        """从字典创建实例"""
        return cls(**data)


class MemoryPrivacyConfig(BaseModel):
    """
    记忆隐私配置

    控制记忆系统的隐私行为，包括存储位置、同步策略和敏感信息过滤。

    Attributes:
        privacy_mode: 全局隐私模式
        sync_strategy: 同步策略
        auto_extract: 是否自动提取记忆
        exclusion_patterns: 提取时排除的敏感关键词（正则列表）
        type_privacy: 按类型设置（可覆盖全局设置）
        sync_interval_seconds: 定期同步间隔（秒）
    """

    # 全局隐私模式
    privacy_mode: PrivacyMode = Field(default=PrivacyMode.SERVER, description="全局隐私模式")

    # 同步策略
    sync_strategy: SyncStrategy = Field(default=SyncStrategy.PERIODIC, description="同步策略")

    # 自动提取设置
    auto_extract: bool = Field(default=True, description="是否自动提取记忆")

    # 提取时排除的敏感关键词（正则列表）
    exclusion_patterns: list[str] = Field(default_factory=list, description="敏感信息排除正则列表")

    # 按类型设置（可覆盖全局设置）
    type_privacy: TypePrivacySettings = Field(
        default_factory=TypePrivacySettings, description="按记忆类型的隐私设置"
    )

    # 定期同步间隔（秒）
    sync_interval_seconds: int = Field(
        default=300, ge=60, le=86400, description="定期同步间隔（秒，60-86400）"
    )

    @field_validator("exclusion_patterns")
    @classmethod
    def validate_exclusion_patterns(cls, patterns: list[str]) -> list[str]:
        """验证排除模式是否为有效正则表达式"""
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f"无效的正则表达式 '{pattern}': {e}") from e
        return patterns

    def should_store_on_server(self, memory_type: str) -> bool:
        """
        判断某类型记忆是否应存储在服务器

        Args:
            memory_type: 记忆类型（user/feedback/project/reference）

        Returns:
            True 如果应该存储在服务器，False 如果只应本地存储
        """
        mode = self.get_effective_mode(memory_type)

        if mode == PrivacyMode.SERVER:
            return True
        if mode == PrivacyMode.LOCAL:
            return False
        # HYBRID
        # 混合模式下，敏感类型本地存储，其他服务器存储
        return memory_type not in {"user", "feedback"}

    def should_auto_sync(self) -> bool:
        """
        判断是否应自动同步

        Returns:
            True 如果应该自动同步（REALTIME 或 PERIODIC）
        """
        return self.sync_strategy in (SyncStrategy.REALTIME, SyncStrategy.PERIODIC)

    def contains_sensitive_info(self, text: str) -> bool:
        """
        检查文本是否包含敏感信息（匹配排除模式）

        Args:
            text: 要检查的文本

        Returns:
            True 如果包含敏感信息
        """
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in self.exclusion_patterns)

    def get_effective_mode(self, memory_type: str) -> PrivacyMode:
        """
        获取指定记忆类型的有效隐私模式

        Args:
            memory_type: 记忆类型

        Returns:
            该类型的有效隐私模式
        """
        # 使用 getattr 获取类型特定设置，如果无效则回退到全局设置
        type_mode: PrivacyMode | None = getattr(self.type_privacy, memory_type, None)

        # 如果类型特定设置是默认值 SERVER 且全局不是 SERVER，则使用全局设置
        if type_mode == PrivacyMode.SERVER and self.privacy_mode != PrivacyMode.SERVER:
            return self.privacy_mode
        return type_mode if type_mode else self.privacy_mode

    def to_safe_dict(self) -> dict[str, Any]:
        """
        转换为安全的字典（不包含敏感的正则模式）

        Returns:
            不包含 exclusion_patterns 的字典
        """
        data = self.model_dump()
        data.pop("exclusion_patterns", None)
        return data


class UserPrivacyPreferences(BaseModel):
    """
    用户隐私偏好存储

    存储用户的完整隐私配置，包含用户ID和时间戳。

    Attributes:
        user_id: 用户唯一标识
        memory_config: 记忆隐私配置
        updated_at: 最后更新时间
    """

    user_id: str = Field(..., description="用户唯一标识")
    memory_config: MemoryPrivacyConfig = Field(
        default_factory=MemoryPrivacyConfig, description="记忆隐私配置"
    )
    updated_at: datetime = Field(default_factory=datetime.now, description="最后更新时间")

    def update_config(self, new_config: MemoryPrivacyConfig) -> None:
        """更新配置并刷新时间戳"""
        self.memory_config = new_config
        self.updated_at = datetime.now()

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════
# 默认配置实例
# ═══════════════════════════════════════════════════════════


def create_default_privacy_config() -> MemoryPrivacyConfig:
    """创建默认隐私配置"""
    return MemoryPrivacyConfig()


def create_local_only_config() -> MemoryPrivacyConfig:
    """创建仅本地存储配置"""
    return MemoryPrivacyConfig(
        privacy_mode=PrivacyMode.LOCAL,
        sync_strategy=SyncStrategy.MANUAL,
        auto_extract=True,
    )


def create_hybrid_config() -> MemoryPrivacyConfig:
    """创建混合模式配置（敏感信息本地，其他服务器）"""
    return MemoryPrivacyConfig(
        privacy_mode=PrivacyMode.HYBRID,
        sync_strategy=SyncStrategy.PERIODIC,
        auto_extract=True,
        type_privacy=TypePrivacySettings(
            user=PrivacyMode.LOCAL,
            feedback=PrivacyMode.LOCAL,
            project=PrivacyMode.SERVER,
            reference=PrivacyMode.SERVER,
        ),
    )


def create_enterprise_config() -> MemoryPrivacyConfig:
    """创建企业级隐私配置（严格本地存储，敏感信息过滤）"""
    return MemoryPrivacyConfig(
        privacy_mode=PrivacyMode.LOCAL,
        sync_strategy=SyncStrategy.MANUAL,
        auto_extract=False,  # 企业环境禁用自动提取
        exclusion_patterns=[
            r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # 信用卡号
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # 邮箱
            r"password\s*[=:]\s*\S+",  # 密码
            r"api[_-]?key\s*[=:]\s*\S+",  # API Key
            r"token\s*[=:]\s*\S+",  # Token
            r"secret\s*[=:]\s*\S+",  # Secret
        ],
    )


__all__ = [
    "PrivacyMode",
    "SyncStrategy",
    "TypePrivacySettings",
    "MemoryPrivacyConfig",
    "UserPrivacyPreferences",
    "create_default_privacy_config",
    "create_local_only_config",
    "create_hybrid_config",
    "create_enterprise_config",
]
