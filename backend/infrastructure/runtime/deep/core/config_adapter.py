"""Config Adapter - 配置适配器"""

from typing import Any

from pydantic import BaseModel, Field


class DeepAgentConfig(BaseModel):
    """Deep Agent 配置

    用于配置 Deep Agent Runtime 的参数。
    """

    name: str = Field(default="agent", description="Agent 名称")
    model: str | None = Field(
        default=None, description="模型名称（None 表示使用 ProviderManager 配置）"
    )
    system: str = Field(default="", description="系统提示词")
    system_prompt: str = Field(default="", description="系统提示词（别名）")
    skills: list[str] = Field(default_factory=list, description="技能列表")
    subagents: list[Any] = Field(default_factory=list, description="子代理列表")
    interrupt_on: dict[str, Any] = Field(default_factory=dict, description="中断配置")

    class Config:
        """Pydantic 配置"""

        populate_by_name = True


__all__ = ["DeepAgentConfig"]
