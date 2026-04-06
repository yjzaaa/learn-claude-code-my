"""
Skill Engine Configuration - Skill Engine 配置模块

包含 SkillEngineConfig 数据类和配置加载逻辑。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.infrastructure.config import config as app_config


@dataclass
class SkillEmbeddingConfig:
    """技能 Embedding 配置"""

    enabled: bool = True
    model: str = "openai/text-embedding-3-small"
    max_chars: int = 12_000  # 文本截断长度
    cache_dir: str = ".skill_embedding_cache"
    cache_file: str = "skill_embeddings_v1.pkl"


@dataclass
class SkillTwoPhaseConfig:
    """两阶段执行配置"""

    enabled: bool = True
    cleanup_workspace: bool = True  # 回退前清理工作区
    full_iterations_on_fallback: bool = True  # 回退阶段使用完整迭代预算


@dataclass
class SkillEvolutionConfig:
    """技能进化配置"""

    enabled: bool = False  # 默认关闭，第一阶段只分析不进化
    auto_fix: bool = False  # 自动生成 FIX 技能
    auto_derive: bool = False  # 自动提取 DERIVED 技能
    min_executions_for_analysis: int = 5  # 最小执行次数才进行分析


@dataclass
class SkillQualityConfig:
    """技能质量追踪配置"""

    enabled: bool = True
    data_file: str = "skill_quality.jsonl"
    filter_problematic: bool = True  # 自动过滤问题技能
    never_completed_threshold: int = 2
    fallback_ratio_threshold: float = 0.5
    min_applied_for_filter: int = 2


@dataclass
class SkillEngineConfig:
    """Skill Engine 总配置"""

    enabled: bool = True
    max_select: int = 2  # 最大选择技能数
    prefilter_threshold: int = 10  # BM25 预过滤阈值
    bm25_candidates_multiplier: int = 3  # BM25 候选数倍数

    embedding: SkillEmbeddingConfig = field(default_factory=SkillEmbeddingConfig)
    two_phase: SkillTwoPhaseConfig = field(default_factory=SkillTwoPhaseConfig)
    evolution: SkillEvolutionConfig = field(default_factory=SkillEvolutionConfig)
    quality: SkillQualityConfig = field(default_factory=SkillQualityConfig)

    @classmethod
    def from_app_config(cls) -> "SkillEngineConfig":
        """从应用配置创建 SkillEngineConfig

        读取 config.yaml 中的 skill.* 配置项
        """
        # 获取原始配置字典
        raw_config: dict[str, Any] = {}
        try:
            import yaml

            config_path = Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "config.yaml"
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    full_config = yaml.safe_load(f) or {}
                    raw_config = full_config.get("skill", {})
        except Exception:
            pass  # 使用默认配置

        # 构建 embedding 配置
        embedding_cfg = raw_config.get("embedding", {})
        embedding = SkillEmbeddingConfig(
            enabled=embedding_cfg.get("enabled", True),
            model=embedding_cfg.get(
                "model",
                app_config.api_keys.openai and "openai/text-embedding-3-small"
                or "openai/text-embedding-3-small",
            ),
            max_chars=embedding_cfg.get("max_chars", 12_000),
            cache_dir=embedding_cfg.get("cache_dir", ".skill_embedding_cache"),
            cache_file=embedding_cfg.get("cache_file", "skill_embeddings_v1.pkl"),
        )

        # 构建两阶段配置
        two_phase_cfg = raw_config.get("two_phase", {})
        two_phase = SkillTwoPhaseConfig(
            enabled=two_phase_cfg.get("enabled", True),
            cleanup_workspace=two_phase_cfg.get("cleanup_workspace", True),
            full_iterations_on_fallback=two_phase_cfg.get("full_iterations_on_fallback", True),
        )

        # 构建进化配置
        evolution_cfg = raw_config.get("evolution", {})
        evolution = SkillEvolutionConfig(
            enabled=evolution_cfg.get("enabled", False),
            auto_fix=evolution_cfg.get("auto_fix", False),
            auto_derive=evolution_cfg.get("auto_derive", False),
            min_executions_for_analysis=evolution_cfg.get("min_executions_for_analysis", 5),
        )

        # 构建质量追踪配置
        quality_cfg = raw_config.get("quality", {})
        quality = SkillQualityConfig(
            enabled=quality_cfg.get("enabled", True),
            data_file=quality_cfg.get("data_file", "skill_quality.jsonl"),
            filter_problematic=quality_cfg.get("filter_problematic", True),
            never_completed_threshold=quality_cfg.get("never_completed_threshold", 2),
            fallback_ratio_threshold=quality_cfg.get("fallback_ratio_threshold", 0.5),
            min_applied_for_filter=quality_cfg.get("min_applied_for_filter", 2),
        )

        return cls(
            enabled=raw_config.get("enabled", True),
            max_select=raw_config.get("max_select", 2),
            prefilter_threshold=raw_config.get("prefilter_threshold", 10),
            bm25_candidates_multiplier=raw_config.get("bm25_candidates_multiplier", 3),
            embedding=embedding,
            two_phase=two_phase,
            evolution=evolution,
            quality=quality,
        )

    def get_cache_path(self) -> Path:
        """获取 embedding 缓存文件路径"""
        cache_dir = Path(self.embedding.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / self.embedding.cache_file

    def get_quality_data_path(self) -> Path:
        """获取质量数据文件路径"""
        return Path(self.quality.data_file)
