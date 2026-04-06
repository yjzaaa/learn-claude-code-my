"""
Tests for SkillRanker

Tests for BM25 + Embedding hybrid ranking, caching, and fallback behavior.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.infrastructure.services.skill_ranker import (
    PREFILTER_THRESHOLD,
    SKILL_BODY_MAX_CHARS,
    SKILL_EMBEDDING_MAX_CHARS,
    RankedSkill,
    SkillRanker,
)


@pytest.fixture
def mock_skill():
    """Create a mock skill for testing"""
    skill = MagicMock()
    skill.id = "test-skill"
    skill.definition.name = "Test Skill"
    skill.definition.description = "A test skill for unit testing"
    skill.path = "/tmp/test-skill"
    return skill


@pytest.fixture
def mock_skills():
    """Create multiple mock skills for testing"""
    skills = []
    for i in range(15):
        skill = MagicMock()
        skill.id = f"skill-{i}"
        skill.definition.name = f"Skill {i}"
        skill.definition.description = f"Description for skill {i}"
        skill.path = f"/tmp/skill-{i}"
        skills.append(skill)
    return skills


@pytest.fixture
def ranker():
    """Create a SkillRanker instance with embedding disabled"""
    return SkillRanker(embedding_enabled=False)


class TestSkillRankerInitialization:
    """Test SkillRanker initialization"""

    def test_init_default(self):
        ranker = SkillRanker()
        assert ranker.embedding_enabled is True
        assert ranker.embedding_model == "text-embedding-3-small"

    def test_init_custom(self):
        ranker = SkillRanker(
            embedding_enabled=False,
            embedding_model="custom-model",
        )
        assert ranker.embedding_enabled is False
        assert ranker.embedding_model == "custom-model"

    def test_init_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "env-model")
        ranker = SkillRanker()
        assert ranker.embedding_model == "env-model"


class TestBuildEmbeddingText:
    """Test _build_embedding_text method"""

    def test_build_text_basic(self, ranker, mock_skill):
        with patch.object(Path, "exists", return_value=False):
            text = ranker._build_embedding_text(mock_skill)

        assert "Test Skill" in text
        assert "A test skill for unit testing" in text
        # When no body, format is "{name}\n{description}" (no double newline)
        assert "\n" in text

    def test_build_text_with_body(self, ranker, mock_skill, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""
---
name: test-skill
description: Test description
---

# Skill Body

This is the skill body content.
More content here.
""")
        mock_skill.path = str(skill_dir)

        text = ranker._build_embedding_text(mock_skill)

        assert "Test Skill" in text
        assert "Skill Body" in text
        assert "This is the skill body content" in text

    def test_build_text_truncation(self, ranker, mock_skill, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        long_body = "A" * (SKILL_BODY_MAX_CHARS + 1000)
        skill_md.write_text(f"""
---
name: test-skill
description: Test
---

{long_body}
""")
        mock_skill.path = str(skill_dir)

        text = ranker._build_embedding_text(mock_skill)

        assert len(text) <= SKILL_EMBEDDING_MAX_CHARS + 10  # Allow for "..."
        assert "..." in text or len(long_body) <= SKILL_BODY_MAX_CHARS


class TestTokenize:
    """Test _tokenize method"""

    def test_tokenize_simple(self, ranker):
        tokens = ranker._tokenize("Hello world test")
        assert tokens == ["hello", "world", "test"]

    def test_tokenize_with_punctuation(self, ranker):
        tokens = ranker._tokenize("Hello, world! Test.")
        assert tokens == ["hello", "world", "test"]

    def test_tokenize_empty(self, ranker):
        tokens = ranker._tokenize("")
        assert tokens == []

    def test_tokenize_case_insensitive(self, ranker):
        tokens = ranker._tokenize("HELLO World")
        assert tokens == ["hello", "world"]


class TestBM25Rank:
    """Test _bm25_rank method"""

    def test_bm25_rank_empty_skills(self, ranker):
        results = ranker._bm25_rank("query", [], 5)
        assert results == []

    def test_bm25_rank_empty_query(self, ranker, mock_skills):
        results = ranker._bm25_rank("", mock_skills, 5)
        assert len(results) == 5
        # All should have score 0.0
        assert all(score == 0.0 for _, score in results)

    def test_bm25_rank_returns_top_k(self, ranker, mock_skills):
        results = ranker._bm25_rank("test query", mock_skills, 5)
        assert len(results) == 5

    def test_bm25_rank_sorted_by_score(self, ranker, mock_skills):
        results = ranker._bm25_rank("skill 5", mock_skills, 10)
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)


class TestTokenOverlapRank:
    """Test _token_overlap_rank fallback method"""

    def test_token_overlap_basic(self, ranker, mock_skills):
        results = ranker._token_overlap_rank("skill 5", mock_skills, 5)
        assert len(results) == 5

    def test_token_overlap_exact_match(self, ranker):
        skill1 = MagicMock()
        skill1.id = "python"
        skill1.definition.name = "python"
        skill1.definition.description = "python programming"
        skill1.path = None

        skill2 = MagicMock()
        skill2.id = "java"
        skill2.definition.name = "java"
        skill2.definition.description = "java programming"
        skill2.path = None

        results = ranker._token_overlap_rank("python", [skill1, skill2], 2)
        assert results[0][0].id == "python"
        assert results[0][1] > results[1][1]


class TestCosineSimilarity:
    """Test _cosine_similarity method"""

    def test_identical_vectors(self, ranker):
        a = [1.0, 2.0, 3.0]
        b = [1.0, 2.0, 3.0]
        similarity = ranker._cosine_similarity(a, b)
        assert similarity == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors(self, ranker):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        similarity = ranker._cosine_similarity(a, b)
        assert similarity == pytest.approx(0.0, abs=1e-6)

    def test_opposite_vectors(self, ranker):
        a = [1.0, 0.0, 0.0]
        b = [-1.0, 0.0, 0.0]
        similarity = ranker._cosine_similarity(a, b)
        assert similarity == pytest.approx(-1.0, abs=1e-6)

    def test_zero_vector(self, ranker):
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        similarity = ranker._cosine_similarity(a, b)
        assert similarity == 0.0

    def test_different_dimensions(self, ranker):
        a = [1.0, 2.0]
        b = [1.0, 2.0, 3.0]
        similarity = ranker._cosine_similarity(a, b)
        assert similarity == 0.0


class TestHybridRank:
    """Test hybrid_rank method"""

    @pytest.mark.asyncio
    async def test_hybrid_rank_empty_skills(self, ranker):
        results = await ranker.hybrid_rank("query", [], 5)
        assert results == []

    @pytest.mark.asyncio
    async def test_hybrid_rank_empty_query(self, ranker, mock_skills):
        results = await ranker.hybrid_rank("", mock_skills, 5)
        assert len(results) == 5
        assert all(r.final_score == 0.0 for r in results)

    @pytest.mark.asyncio
    async def test_hybrid_rank_returns_top_k(self, ranker, mock_skills):
        results = await ranker.hybrid_rank("test", mock_skills, 5)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_hybrid_rank_returns_ranked_skill_objects(self, ranker, mock_skills):
        results = await ranker.hybrid_rank("test", mock_skills, 5)
        assert all(isinstance(r, RankedSkill) for r in results)

    @pytest.mark.asyncio
    async def test_hybrid_rank_below_prefilter_threshold(self, ranker, mock_skills):
        """When skills < PREFILTER_THRESHOLD, skip BM25 pre-filter"""
        skills = mock_skills[:5]  # Less than threshold
        results = await ranker.hybrid_rank("test", skills, 3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_hybrid_rank_above_prefilter_threshold(self, ranker, mock_skills):
        """When skills > PREFILTER_THRESHOLD, use BM25 pre-filter"""
        assert len(mock_skills) > PREFILTER_THRESHOLD
        results = await ranker.hybrid_rank("test", mock_skills, 5)
        # Should return top_k, not top_k * 3
        assert len(results) == 5


class TestEmbeddingRank:
    """Test _embedding_rank method"""

    @pytest.mark.asyncio
    async def test_embedding_rank_disabled(self, ranker, mock_skills):
        ranker.embedding_enabled = False
        # Should not be called when disabled
        pass

    @pytest.mark.asyncio
    async def test_embedding_rank_empty_skills(self, ranker):
        results = await ranker._embedding_rank("query", [], 5)
        assert results == []

    @pytest.mark.asyncio
    async def test_embedding_rank_with_mock_embedding(self, ranker, mock_skills):
        """Test embedding rank with mocked embedding generation"""
        ranker.embedding_enabled = True

        # Mock embeddings: query and skills have different vectors
        query_embedding = [1.0, 0.0, 0.0]
        skill_embeddings = {
            "skill-0": [1.0, 0.0, 0.0],  # Most similar
            "skill-1": [0.0, 1.0, 0.0],  # Orthogonal
            "skill-2": [0.0, 0.0, 1.0],  # Orthogonal
        }

        async def mock_generate_embedding(text):
            if "query" in text.lower():
                return query_embedding
            for skill_id, emb in skill_embeddings.items():
                if skill_id in text:
                    return emb
            return [0.0, 0.0, 0.0]

        ranker._generate_embedding = mock_generate_embedding
        ranker._cache.clear()

        # Override _get_skill_embedding to use our mock
        async def mock_get_skill_embedding(skill):
            return skill_embeddings.get(skill.id, [0.0, 0.0, 0.0])

        ranker._get_skill_embedding = mock_get_skill_embedding

        results = await ranker._embedding_rank("query", mock_skills[:3], 3)

        assert len(results) == 3
        # skill-0 should have highest score (identical to query)
        assert results[0][0].id == "skill-0"
        assert results[0][1] == pytest.approx(1.0, abs=1e-6)


class TestCache:
    """Test caching functionality"""

    def test_cache_stats(self, ranker):
        stats = ranker.get_cache_stats()
        assert "cached_count" in stats
        assert "cache_file" in stats
        assert "cache_exists" in stats
        assert "embedding_enabled" in stats

    def test_clear_cache(self, ranker):
        ranker._cache = {"test": ([1.0, 2.0], "hash")}
        with patch.object(Path, "exists", return_value=False):
            ranker.clear_cache()
        assert len(ranker._cache) == 0

    def test_get_skill_mtime_hash_no_path(self, ranker, mock_skill):
        mock_skill.path = None
        result = ranker._get_skill_mtime_hash(mock_skill)
        assert result == ""

    def test_get_skill_mtime_hash_with_path(self, ranker, mock_skill, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("test content")
        mock_skill.path = str(skill_dir)

        result = ranker._get_skill_mtime_hash(mock_skill)
        assert result != ""
        assert "_" in result  # Format: mtime_hash


class TestGenerateEmbedding:
    """Test _generate_embedding method"""

    @pytest.mark.asyncio
    async def test_generate_embedding_no_api_key(self, ranker):
        with patch("backend.infrastructure.services.skill_ranker.config") as mock_config:
            mock_config.api_keys.openai = ""
            result = await ranker._generate_embedding("test text")
            assert result is None

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, ranker):
        mock_embedding = [0.1, 0.2, 0.3]

        with patch("backend.infrastructure.services.skill_ranker.config") as mock_config:
            mock_config.api_keys.openai = "test-key"
            mock_config.api_keys.openai_base_url = ""

            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=mock_embedding)]

            mock_client = AsyncMock()
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            with patch("openai.AsyncOpenAI", return_value=mock_client):
                result = await ranker._generate_embedding("test text")

        assert result == mock_embedding

    @pytest.mark.asyncio
    async def test_generate_embedding_api_error(self, ranker):
        with patch("backend.infrastructure.services.skill_ranker.config") as mock_config:
            mock_config.api_keys.openai = "test-key"
            mock_config.api_keys.openai_base_url = ""

            mock_client = AsyncMock()
            mock_client.embeddings.create = AsyncMock(side_effect=Exception("API Error"))

            with patch("openai.AsyncOpenAI", return_value=mock_client):
                result = await ranker._generate_embedding("test text")

        assert result is None


class TestIntegration:
    """Integration tests for full hybrid ranking flow"""

    @pytest.mark.asyncio
    async def test_full_hybrid_rank_flow(self, ranker, mock_skills):
        """Test the complete hybrid ranking flow without embedding"""
        results = await ranker.hybrid_rank("skill description", mock_skills, 3)

        assert len(results) == 3
        assert all(isinstance(r, RankedSkill) for r in results)
        assert all(hasattr(r, "skill") for r in results)
        assert all(hasattr(r, "final_score") for r in results)

    @pytest.mark.asyncio
    async def test_ranked_skill_structure(self, ranker, mock_skills):
        results = await ranker.hybrid_rank("test", mock_skills, 3)

        for ranked in results:
            assert hasattr(ranked, "skill")
            assert hasattr(ranked, "bm25_score")
            assert hasattr(ranked, "embedding_score")
            assert hasattr(ranked, "final_score")
            assert ranked.final_score >= 0.0
