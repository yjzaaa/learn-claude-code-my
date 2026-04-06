"""
Skill Ranker - BM25 + Embedding 混合排序

实现两阶段技能排序：
1. BM25 快速预过滤
2. Embedding 语义重排序

支持本地缓存 embedding，避免重复计算。
"""

from __future__ import annotations

import hashlib
import os
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from backend.infrastructure.config import config
from backend.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from backend.domain.models.agent.skill import Skill

logger = get_logger(__name__)

# 预过滤阈值：技能数量超过此值才使用 BM25 预过滤
PREFILTER_THRESHOLD = 10
# BM25 预过滤倍数：返回 top_k * 3 个候选
BM25_PREFILTER_MULTIPLIER = 3
# Embedding 文本最大长度
SKILL_EMBEDDING_MAX_CHARS = 12_000
# 技能 body 截断长度
SKILL_BODY_MAX_CHARS = 8_000
# 默认 embedding 模型
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
# 缓存文件路径
CACHE_DIR = Path(".skill_embedding_cache")
CACHE_FILE = CACHE_DIR / "skill_embeddings_v1.pkl"


@dataclass
class RankedSkill:
    """排序后的技能结果"""

    skill: Skill
    bm25_score: float = 0.0
    embedding_score: float = 0.0
    final_score: float = 0.0


class SkillRanker:
    """技能排序器

    使用 BM25 + Embedding 混合排序算法：
    1. BM25 快速预过滤，缩小候选集
    2. Embedding 语义重排序，提升准确率

    Attributes:
        embedding_enabled: 是否启用 embedding 排序
        embedding_model: 使用的 embedding 模型
        _cache: embedding 缓存字典 {skill_id: (embedding, mtime_hash)}
        _bm25_available: BM25 库是否可用
    """

    def __init__(
        self,
        embedding_enabled: bool = True,
        embedding_model: str | None = None,
    ):
        """初始化 SkillRanker

        Args:
            embedding_enabled: 是否启用 embedding 排序
            embedding_model: 使用的 embedding 模型，默认 text-embedding-3-small
        """
        self.embedding_enabled = embedding_enabled
        self.embedding_model = embedding_model or self._get_embedding_model()
        self._cache: dict[str, tuple[list[float], str]] = {}
        self._bm25_available = self._check_bm25_available()

        # 加载缓存
        self._load_cache()

    def _check_bm25_available(self) -> bool:
        """检查 rank-bm25 库是否可用"""
        try:
            from rank_bm25 import BM25Okapi

            return True
        except ImportError:
            logger.warning("[SkillRanker] rank-bm25 not available, using token overlap fallback")
            return False

    def _get_embedding_model(self) -> str:
        """获取 embedding 模型配置"""
        # 优先级：环境变量 > 配置默认值
        return os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)

    def _load_cache(self) -> None:
        """从磁盘加载 embedding 缓存"""
        if not CACHE_FILE.exists():
            logger.debug("[SkillRanker] No cache file found")
            return

        try:
            with open(CACHE_FILE, "rb") as f:
                self._cache = pickle.load(f)
            logger.info(f"[SkillRanker] Loaded {len(self._cache)} cached embeddings")
        except Exception as e:
            logger.error(f"[SkillRanker] Failed to load cache: {e}")
            self._cache = {}

    def _save_cache(self) -> None:
        """保存 embedding 缓存到磁盘"""
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "wb") as f:
                pickle.dump(self._cache, f)
            logger.debug(f"[SkillRanker] Saved {len(self._cache)} embeddings to cache")
        except Exception as e:
            logger.error(f"[SkillRanker] Failed to save cache: {e}")

    def _get_skill_mtime_hash(self, skill: Skill) -> str:
        """获取技能文件的修改时间哈希

        Args:
            skill: 技能实例

        Returns:
            mtime 哈希字符串
        """
        if not skill.path:
            return ""

        skill_md_path = Path(skill.path) / "SKILL.md"
        if not skill_md_path.exists():
            return ""

        try:
            mtime = skill_md_path.stat().st_mtime
            content_hash = hashlib.md5(skill_md_path.read_bytes()).hexdigest()[:8]
            return f"{mtime}_{content_hash}"
        except Exception:
            return ""

    def _build_embedding_text(self, skill: Skill) -> str:
        """构建用于 embedding 的文本

        格式: "{name}\n{description}\n\n{body[:8000]}"

        Args:
            skill: 技能实例

        Returns:
            格式化后的文本
        """
        name = skill.definition.name
        description = skill.definition.description

        # 读取 SKILL.md body
        body = ""
        if skill.path:
            skill_md_path = Path(skill.path) / "SKILL.md"
            if skill_md_path.exists():
                try:
                    content = skill_md_path.read_text(encoding="utf-8")
                    # 解析 front-matter，获取 body
                    if content.startswith("---"):
                        end = content.find("---", 3)
                        if end >= 0:
                            body = content[end + 3 :].strip()
                        else:
                            body = content
                    else:
                        body = content
                except Exception:
                    pass

        # 截断 body
        if len(body) > SKILL_BODY_MAX_CHARS:
            body = body[:SKILL_BODY_MAX_CHARS] + "..."

        # 构建完整文本
        text = f"{name}\n{description}"
        if body:
            text += f"\n\n{body}"

        # 最终截断
        if len(text) > SKILL_EMBEDDING_MAX_CHARS:
            text = text[:SKILL_EMBEDDING_MAX_CHARS]

        return text

    async def _generate_embedding(self, text: str) -> list[float] | None:
        """生成文本的 embedding

        使用 OpenAI API 或兼容 API。

        Args:
            text: 输入文本

        Returns:
            embedding 向量，失败返回 None
        """
        try:
            import openai

            # 获取 API key
            api_key = config.api_keys.openai
            if not api_key:
                logger.warning("[SkillRanker] No OpenAI API key configured")
                return None

            # 创建客户端
            base_url = config.api_keys.openai_base_url
            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=base_url if base_url else None,
            )

            # 调用 API
            response = await client.embeddings.create(
                model=self.embedding_model,
                input=text[:SKILL_EMBEDDING_MAX_CHARS],
            )

            embedding = response.data[0].embedding
            logger.debug(f"[SkillRanker] Generated embedding with {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            logger.error(f"[SkillRanker] Failed to generate embedding: {e}")
            return None

    async def _get_skill_embedding(self, skill: Skill) -> list[float] | None:
        """获取技能的 embedding（带缓存）

        Args:
            skill: 技能实例

        Returns:
            embedding 向量，失败返回 None
        """
        skill_id = skill.id
        mtime_hash = self._get_skill_mtime_hash(skill)

        # 检查缓存
        if skill_id in self._cache:
            cached_embedding, cached_hash = self._cache[skill_id]
            if cached_hash == mtime_hash:
                logger.debug(f"[SkillRanker] Cache hit for skill '{skill_id}'")
                return cached_embedding
            else:
                logger.debug(f"[SkillRanker] Cache invalidated for skill '{skill_id}'")

        # 生成新的 embedding
        text = self._build_embedding_text(skill)
        embedding = await self._generate_embedding(text)

        if embedding:
            # 更新缓存
            self._cache[skill_id] = (embedding, mtime_hash)
            self._save_cache()
            logger.debug(f"[SkillRanker] Cached embedding for skill '{skill_id}'")

        return embedding

    def _tokenize(self, text: str) -> list[str]:
        """简单的 tokenization

        Args:
            text: 输入文本

        Returns:
            token 列表
        """
        # 简单的空格和标点分词
        import re

        text = text.lower()
        tokens = re.findall(r"\b\w+\b", text)
        return tokens

    def _bm25_rank(
        self,
        query: str,
        skills: list[Skill],
        top_k: int,
    ) -> list[tuple[Skill, float]]:
        """使用 BM25 排序技能

        Args:
            query: 用户查询
            skills: 技能列表
            top_k: 返回前 k 个

        Returns:
            [(skill, score), ...] 按分数降序
        """
        if not skills:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return [(skill, 0.0) for skill in skills[:top_k]]

        if self._bm25_available:
            try:
                from rank_bm25 import BM25Okapi

                # 构建语料库
                corpus = []
                for skill in skills:
                    text = self._build_embedding_text(skill)
                    tokens = self._tokenize(text)
                    corpus.append(tokens)

                # 创建 BM25 模型
                bm25 = BM25Okapi(corpus)

                # 计算分数
                scores = bm25.get_scores(query_tokens)

                # 排序
                scored_skills = list(zip(skills, scores, strict=False))
                scored_skills.sort(key=lambda x: x[1], reverse=True)

                return scored_skills[:top_k]

            except Exception as e:
                logger.error(f"[SkillRanker] BM25 error: {e}, falling back to token overlap")

        # 回退：简单的 token 重叠
        return self._token_overlap_rank(query, skills, top_k)

    def _token_overlap_rank(
        self,
        query: str,
        skills: list[Skill],
        top_k: int,
    ) -> list[tuple[Skill, float]]:
        """使用 token 重叠度排序（BM25 不可用时回退）

        Args:
            query: 用户查询
            skills: 技能列表
            top_k: 返回前 k 个

        Returns:
            [(skill, score), ...] 按分数降序
        """
        query_tokens = set(self._tokenize(query))
        if not query_tokens:
            return [(skill, 0.0) for skill in skills[:top_k]]

        scored_skills = []
        for skill in skills:
            text = self._build_embedding_text(skill)
            skill_tokens = set(self._tokenize(text))

            # Jaccard 相似度
            intersection = len(query_tokens & skill_tokens)
            union = len(query_tokens | skill_tokens)
            score = intersection / union if union > 0 else 0.0

            scored_skills.append((skill, score))

        scored_skills.sort(key=lambda x: x[1], reverse=True)
        return scored_skills[:top_k]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """计算两个向量的余弦相似度

        Args:
            a: 向量 a
            b: 向量 b

        Returns:
            余弦相似度 [-1, 1]
        """
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    async def _embedding_rank(
        self,
        query: str,
        skills: list[Skill],
        top_k: int,
    ) -> list[tuple[Skill, float]]:
        """使用 embedding 语义排序技能

        Args:
            query: 用户查询
            skills: 技能列表
            top_k: 返回前 k 个

        Returns:
            [(skill, score), ...] 按分数降序
        """
        if not skills:
            return []

        # 生成查询的 embedding
        query_embedding = await self._generate_embedding(query)
        if not query_embedding:
            logger.warning("[SkillRanker] Failed to generate query embedding, returning BM25 order")
            return [(skill, 0.0) for skill in skills[:top_k]]

        # 计算每个技能的相似度
        scored_skills = []
        for skill in skills:
            skill_embedding = await self._get_skill_embedding(skill)
            if skill_embedding:
                similarity = self._cosine_similarity(query_embedding, skill_embedding)
                scored_skills.append((skill, similarity))
            else:
                scored_skills.append((skill, 0.0))

        # 排序
        scored_skills.sort(key=lambda x: x[1], reverse=True)
        return scored_skills[:top_k]

    async def hybrid_rank(
        self,
        query: str,
        skills: list[Skill],
        top_k: int = 10,
    ) -> list[RankedSkill]:
        """混合排序：BM25 预过滤 + Embedding 重排序

        流程：
        1. 如果技能数量 > PREFILTER_THRESHOLD，使用 BM25 预过滤到 top_k * 3
        2. 对候选技能使用 embedding 重排序
        3. 如果 embedding 禁用或失败，返回 BM25 结果

        Args:
            query: 用户查询
            skills: 技能列表
            top_k: 返回前 k 个技能

        Returns:
            RankedSkill 列表，按相关性降序
        """
        if not skills:
            return []

        if not query.strip():
            return [RankedSkill(skill=skill) for skill in skills[:top_k]]

        logger.info(f"[SkillRanker] Ranking {len(skills)} skills for query: {query[:50]}...")

        # 阶段 1: BM25 预过滤
        if len(skills) > PREFILTER_THRESHOLD:
            bm25_top_k = min(top_k * BM25_PREFILTER_MULTIPLIER, len(skills))
            bm25_results = self._bm25_rank(query, skills, bm25_top_k)
            candidates = [skill for skill, _ in bm25_results]
            bm25_scores = {skill.id: score for skill, score in bm25_results}
            logger.debug(f"[SkillRanker] BM25 pre-filtered to {len(candidates)} candidates")
        else:
            # 技能数量少，跳过 BM25 预过滤
            candidates = skills
            bm25_scores = {}

        # 阶段 2: Embedding 重排序
        if self.embedding_enabled and len(candidates) > 1:
            try:
                embedding_results = await self._embedding_rank(query, candidates, top_k)
                ranked_skills = []
                for skill, emb_score in embedding_results:
                    ranked_skills.append(
                        RankedSkill(
                            skill=skill,
                            bm25_score=bm25_scores.get(skill.id, 0.0),
                            embedding_score=emb_score,
                            final_score=emb_score,  # embedding 分数作为最终分数
                        )
                    )
                logger.info(f"[SkillRanker] Hybrid ranking completed, returned {len(ranked_skills)} skills")
                return ranked_skills
            except Exception as e:
                logger.error(f"[SkillRanker] Embedding rank failed: {e}, falling back to BM25")

        # 回退：使用 BM25 结果
        bm25_results = self._bm25_rank(query, skills, top_k)
        return [
            RankedSkill(
                skill=skill,
                bm25_score=score,
                final_score=score,
            )
            for skill, score in bm25_results
        ]

    def clear_cache(self) -> None:
        """清除 embedding 缓存"""
        self._cache.clear()
        if CACHE_FILE.exists():
            try:
                CACHE_FILE.unlink()
                logger.info("[SkillRanker] Cache cleared")
            except Exception as e:
                logger.error(f"[SkillRanker] Failed to clear cache: {e}")

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cached_count": len(self._cache),
            "cache_file": str(CACHE_FILE),
            "cache_exists": CACHE_FILE.exists(),
            "embedding_enabled": self.embedding_enabled,
            "embedding_model": self.embedding_model,
            "bm25_available": self._bm25_available,
        }


__all__ = ["SkillRanker", "RankedSkill"]
