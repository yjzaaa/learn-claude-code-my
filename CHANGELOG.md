# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added - Skill Engine

#### Core Features
- **BM25 + Embedding Hybrid Ranking**: Two-stage skill ranking algorithm
  - BM25 pre-filtering for quick candidate narrowing (>10 skills)
  - Embedding re-ranking using text-embedding-3-small
  - Local embedding cache in `.skill_embedding_cache/`
  
- **Two-Phase Execution**: Skill-First → Tool-Fallback strategy
  - Phase 1: Execute with skill guidance
  - Phase 2: Fallback to tool-only execution on failure
  - Automatic workspace cleanup between phases
  
- **Quality Tracking**: Automatic skill quality metrics
  - Tracks selections, applications, completions, and fallbacks
  - JSONL storage in `skill_quality.jsonl`
  - Automatic filtering of problematic skills
  
- **Backend-Aware Prompt Injection**: Dynamic prompt generation
  - Detects available backends from tool configuration
  - Generates tool-specific hints
  - Replaces `{baseDir}` placeholders with absolute paths
  
- **Skill ID Sidecar**: Persistent skill identification
  - `.skill_id` files in skill directories
  - Supports imported and evolved skill types
  - UUID-based unique identifiers

#### New Components
- `SkillRanker` (`backend/infrastructure/services/skill_ranker.py`)
- `SkillStore` (`backend/infrastructure/persistence/skill_store.py`)
- `SkillIDSidecar` (`backend/infrastructure/services/skill_id_sidecar.py`)
- `SkillEngineMiddleware` (`backend/infrastructure/runtime/deep/middleware/skill_engine.py`)
- `ExecutionAnalyzer` (`backend/infrastructure/services/execution_analyzer.py`)
- `TwoPhaseExecutionMixin` (`backend/infrastructure/runtime/deep/mixins/two_phase.py`)
- `TwoPhaseSkillStoreMixin` (`backend/infrastructure/runtime/deep/mixins/two_phase_skill_store.py`)

#### Configuration
- New `SkillConfig` in `backend/infrastructure/config.py`
- Feature flags for gradual rollout:
  - `skill.enabled`: Master switch
  - `skill.embedding.enabled`: Embedding ranking
  - `skill.two_phase.enabled`: Two-phase execution
  - `skill.quality.filter_problematic`: Quality filtering

#### Documentation
- `docs/ARCHITECTURE.md`: Skill Engine architecture documentation
- `docs/MIGRATION.md`: Migration guide from old skill system
- `skills/example/SKILL.md`: Example skill with best practices

#### Tests
- `tests/infrastructure/test_skill_ranker.py`
- `tests/infrastructure/test_skill_store.py`
- `tests/infrastructure/test_skill_id_sidecar.py`
- `tests/infrastructure/test_execution_analyzer.py`
- `tests/runtime/test_backend_aware_injection.py`
- `tests/runtime/test_skill_engine_integration.py`
- `tests/runtime/test_two_phase_execution.py`

### Migration Notes

This release introduces the new Skill Engine while maintaining full backward compatibility. The old skill loading mechanism continues to work.

**Recommended Rollout Plan:**
1. Phase 1: Enable with BM25 only (`skill.embedding.enabled: false`)
2. Phase 2: Enable two-phase execution (`skill.two_phase.enabled: true`)
3. Phase 3: Enable embedding ranking (`skill.embedding.enabled: true`)
4. Phase 4: Enable quality filtering (`skill.quality.filter_problematic: true`)

See `docs/MIGRATION.md` for detailed migration instructions.

## [Previous Versions]

- Previous changes were not tracked in this changelog.
