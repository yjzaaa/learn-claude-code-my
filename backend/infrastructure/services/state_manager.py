"""
State Manager - 状态管理器

管理全局状态、配置和持久化。
"""

import json
from pathlib import Path
from typing import Any

from backend.domain.models.shared.config import StateConfig
from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)


class StateManager:
    """
    状态管理器

    职责:
    - 管理全局状态
    - 配置管理
    - 持久化 (可选)
    """

    def __init__(self, config: StateConfig | None = None, state_dir: Path | None = None):
        # 支持 Pydantic BaseModel 和 dataclass
        if config is None:
            self._config: dict[str, Any] = {}
        elif hasattr(config, "model_dump"):
            # Pydantic v2
            self._config = config.model_dump()
        elif hasattr(config, "dict"):
            # Pydantic v1
            self._config = config.dict()
        else:
            # dataclass
            import dataclasses

            self._config = dataclasses.asdict(config)

        self._state: dict[str, Any] = {}
        self._state_dir = state_dir

        # 当前 Provider 名称
        self._current_provider: str | None = None

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取状态值

        Args:
            key: 键
            default: 默认值

        Returns:
            值或默认值
        """
        return self._state.get(key, default)

    def set(self, key: str, value: Any):
        """
        设置状态值

        Args:
            key: 键
            value: 值
        """
        self._state[key] = value

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值或默认值
        """
        return self._config.get(key, default)

    def set_current_provider(self, provider_name: str):
        """设置当前 Provider"""
        self._current_provider = provider_name

    def get_current_provider(self) -> str | None:
        """获取当前 Provider"""
        return self._current_provider

    async def load(self):
        """从持久化加载状态"""
        if not self._state_dir:
            return

        state_file = self._state_dir / "state.json"
        if state_file.exists():
            try:
                with open(state_file, encoding="utf-8") as f:
                    self._state = json.load(f)
                logger.info(f"[StateManager] Loaded state from {state_file}")
            except Exception as e:
                logger.error(f"[StateManager] Failed to load state: {e}")

    async def save(self):
        """保存状态到持久化"""
        if not self._state_dir:
            return

        self._state_dir.mkdir(parents=True, exist_ok=True)
        state_file = self._state_dir / "state.json"

        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)
            logger.info(f"[StateManager] Saved state to {state_file}")
        except Exception as e:
            logger.error(f"[StateManager] Failed to save state: {e}")
