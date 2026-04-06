"""Provider Discovery - 模型发现服务

后台异步发现和缓存可用 LLM 模型配置，不阻塞主线程启动。
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ModelConfig:
    """发现的模型配置"""

    model_id: str
    key_var: str
    api_key: str
    base_url: str | None
    client_type: str
    provider: str


class ModelDiscoveryCache:
    """模型发现缓存管理"""

    def __init__(self, cache_dir: Path | None = None):
        if cache_dir is None:
            cache_dir = Path(__file__).resolve().parent.parent.parent.parent / ".cache"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "discovered_models.json"

    def load(self) -> list[ModelConfig]:
        """从缓存加载模型配置"""
        if not self.cache_file.exists():
            return []

        try:
            with open(self.cache_file, encoding="utf-8") as f:
                data = json.load(f)

            configs = []
            for item in data.get("models", []):
                # 过滤掉 api_key 显示，只保留前几位
                api_key = item.get("api_key", "")
                configs.append(
                    ModelConfig(
                        model_id=item["model_id"],
                        key_var=item["key_var"],
                        api_key=api_key,
                        base_url=item.get("base_url"),
                        client_type=item["client_type"],
                        provider=item["provider"],
                    )
                )

            logger.info(f"[ModelDiscovery] Loaded {len(configs)} models from cache")
            return configs
        except Exception as e:
            logger.warning(f"[ModelDiscovery] Failed to load cache: {e}")
            return []

    def save(self, configs: list[ModelConfig]) -> None:
        """保存模型配置到缓存"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "count": len(configs),
                "models": [
                    {
                        "model_id": c.model_id,
                        "key_var": c.key_var,
                        "api_key": c.api_key[:10] + "..." if c.api_key else "",
                        "base_url": c.base_url,
                        "client_type": c.client_type,
                        "provider": c.provider,
                    }
                    for c in configs
                ],
            }

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"[ModelDiscovery] Saved {len(configs)} models to cache")
        except Exception as e:
            logger.warning(f"[ModelDiscovery] Failed to save cache: {e}")


class AsyncModelDiscovery:
    """后台异步模型发现"""

    _instance: Optional["AsyncModelDiscovery"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._cache = ModelDiscoveryCache()
        self._cached_configs: list[ModelConfig] = []
        self._discovery_task: asyncio.Task | None = None
        self._initialized = True

    @property
    def cached_models(self) -> list[ModelConfig]:
        """获取缓存的模型列表"""
        return self._cached_configs.copy()

    def load_cache(self) -> list[ModelConfig]:
        """加载缓存（同步调用，启动时使用）"""
        self._cached_configs = self._cache.load()
        return self._cached_configs

    def start_discovery(self, project_root: Path | None = None) -> None:
        """启动后台异步发现（不阻塞）"""
        if self._discovery_task is not None and not self._discovery_task.done():
            logger.info("[ModelDiscovery] Discovery already running, skipping")
            return

        logger.info("[ModelDiscovery] Starting background discovery...")
        self._discovery_task = asyncio.create_task(self._background_discover(project_root))

    async def _background_discover(self, project_root: Path | None = None) -> None:
        """后台执行发现任务"""
        try:
            from backend.infrastructure.services import model_discovery

            discovered = await model_discovery.discover_available_models(project_root)

            # 转换为 ModelConfig 格式
            configs = [
                ModelConfig(
                    model_id=config.model_id,
                    key_var=config.key_var,
                    api_key=config.api_key,
                    base_url=config.base_url,
                    client_type=config.client_type,
                    provider=config.provider,
                )
                for config in discovered
            ]

            # 更新缓存
            self._cached_configs = configs
            self._cache.save(configs)

            logger.info(
                f"[ModelDiscovery] Background discovery complete: {len(configs)} models found"
            )

        except Exception as e:
            logger.error(f"[ModelDiscovery] Background discovery failed: {e}")

    async def wait_for_discovery(self, timeout: float = 60.0) -> list[ModelConfig]:
        """等待发现完成（用于需要立即可用模型的场景）"""
        if self._discovery_task is None:
            return self._cached_configs

        try:
            await asyncio.wait_for(self._discovery_task, timeout=timeout)
        except TimeoutError:
            logger.warning("[ModelDiscovery] Discovery timeout, returning cached models")

        return self._cached_configs


# 全局发现实例
_discovery_instance: AsyncModelDiscovery | None = None


def get_discovery() -> AsyncModelDiscovery:
    """获取全局发现实例"""
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = AsyncModelDiscovery()
    return _discovery_instance


async def discover_available_models(project_root: Path | None = None) -> list[ModelConfig]:
    """
    发现所有可用的模型配置（后台异步版本）

    启动时立即返回缓存结果，后台执行完整发现。
    如果需要最新结果，调用 wait_for_discovery()。

    Args:
        project_root: 项目根目录

    Returns:
        ModelConfig 列表（缓存或进行中结果）
    """
    discovery = get_discovery()

    # 如果没有缓存，先尝试加载
    if not discovery.cached_models:
        discovery.load_cache()

    # 启动后台发现（不阻塞）
    discovery.start_discovery(project_root)

    return discovery.cached_models


__all__ = ["ModelConfig", "discover_available_models", "AsyncModelDiscovery", "get_discovery"]
