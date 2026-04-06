## 1. Configuration and Types

- [ ] 1.1 Create `SkillEngineConfig` dataclass with all configuration options
- [ ] 1.2 Add config sections: `skill.embedding`, `skill.two_phase`, `skill.evolution`
- [ ] 1.3 Update `backend/infrastructure/config.py` with new skill configuration
- [ ] 1.4 Create type definitions: `SkillCandidate`, `SkillMeta`, `ExecutionAnalysis`
- [ ] 1.5 Define constants: `PREFILTER_THRESHOLD`, `SKILL_EMBEDDING_MODEL`, `BM25_CANDIDATES_MULTIPLIER`

## 2. Skill ID Sidecar Implementation

- [ ] 2.1 Create `_read_or_create_skill_id()` function for sidecar management
- [ ] 2.2 Implement skill ID generation with format `{name}__imp_{uuid8}`
- [ ] 2.3 Add `.skill_id` file read/write logic with error handling
- [ ] 2.4 Update `SkillManager.load_skill_from_directory()` to use sidecar
- [ ] 2.5 Handle sidecar errors gracefully (read-only dirs, corrupted files)
- [ ] 2.6 Add tests for sidecar creation, reading, and persistence

## 3. Skill Ranker (BM25 + Embedding)

- [ ] 3.1 Create `SkillRanker` class with initialization and cache management
- [ ] 3.2 Implement `BM25Okapi` wrapper with fallback to token overlap
- [ ] 3.3 Implement `_bm25_rank()` method with pre-filtering logic
- [ ] 3.4 Implement `_embedding_rank()` using OpenAI-compatible API
- [ ] 3.5 Create `_generate_embedding()` method with retry logic
- [ ] 3.6 Implement embedding cache persistence (pickle to `.skill_embedding_cache/`)
- [ ] 3.7 Add cache invalidation based on file mtime
- [ ] 3.8 Implement `hybrid_rank()` orchestrating BM25 → Embedding pipeline
- [ ] 3.9 Add `_build_embedding_text()` consistent text formatting
- [ ] 3.10 Create unit tests for ranking algorithms and caching

## 4. Skill Store (Quality Tracking)

- [ ] 4.1 Create `SkillStore` class with JSONL persistence
- [ ] 4.2 Implement `_load_quality_data()` from `skill_quality.jsonl`
- [ ] 4.3 Implement `_save_quality_data()` append-only JSONL format
- [ ] 4.4 Add `record_selection()`, `record_application()`, `record_completion()`, `record_fallback()` methods
- [ ] 4.5 Implement quality filtering logic (never-completed, high-fallback)
- [ ] 4.6 Create `get_summary()` method aggregating metrics per skill
- [ ] 4.7 Add `get_problematic_skills()` for filtering
- [ ] 4.8 Implement `sync_from_registry()` to initialize DB records
- [ ] 4.9 Add tests for quality tracking and filtering

## 5. Skill Engine Middleware Core

- [ ] 5.1 Create `SkillEngineMiddleware` class inheriting `AgentMiddleware`
- [ ] 5.2 Implement `__init__()` with SkillManager, SkillStore, SkillRanker injection
- [ ] 5.3 Add configuration validation in initialization
- [ ] 5.4 Implement `abefore_model()` async hook for skill discovery and injection
- [ ] 5.5 Create `_discover_and_rank_skills()` method using SkillRanker
- [ ] 5.6 Implement quality filtering before LLM selection
- [ ] 5.7 Add `_select_skills_with_llm()` for final skill selection
- [ ] 5.8 Implement `_inject_skill_prompts()` for system message modification
- [ ] 5.9 Add `aafter_model()` hook for execution tracking
- [ ] 5.10 Implement error resilience (graceful degradation on failures)

## 6. Two-Phase Execution

- [ ] 6.1 Add `_execute_skill_phase()` method for Phase 1 execution
- [ ] 6.2 Implement workspace snapshot before Phase 1
- [ ] 6.3 Create `_cleanup_workspace()` method for fallback cleanup
- [ ] 6.4 Add `_execute_tool_fallback()` method for Phase 2
- [ ] 6.5 Implement Phase success/failure detection
- [ ] 6.6 Add fallback triggering logic with cleanup
- [ ] 6.7 Ensure full budget allocation for Phase 2
- [ ] 6.8 Track phase metrics (iterations, status, fallback_triggered)
- [ ] 6.9 Add tests for two-phase execution and cleanup

## 7. Backend-Aware Prompt Injection

- [ ] 7.1 Implement `_get_available_backends()` from GroundingClient
- [ ] 7.2 Create `_build_backend_hint()` method mentioning only available tools
- [ ] 7.3 Add `{baseDir}` placeholder replacement logic
- [ ] 7.4 Implement `_build_context_injection()` with header and skill sections
- [ ] 7.5 Add skill separator and metadata formatting
- [ ] 7.6 Implement resource access tips (read_file, list_dir, etc.)
- [ ] 7.7 Add tests for prompt injection with various backend combinations

## 8. Execution Analyzer

- [ ] 8.1 Create `ExecutionAnalyzer` class with LLMClient dependency
- [ ] 8.2 Implement error pattern recognition (missing_tool, parameter_error, timeout)
- [ ] 8.3 Add `_analyze_with_llm()` method for deep analysis
- [ ] 8.4 Create improvement suggestion generation
- [ ] 8.5 Implement `candidate_for_evolution` flagging logic
- [ ] 8.6 Add metadata recording to `metadata.json`
- [ ] 8.7 Ensure async non-blocking execution
- [ ] 8.8 Add tests for pattern recognition and analysis

## 9. Integration with DeepAgentRuntime

- [ ] 9.1 Create `_init_skill_engine()` method in DeepAgentRuntime
- [ ] 9.2 Initialize SkillRanker, SkillStore, SkillRegistry
- [ ] 9.3 Add SkillEngineMiddleware to middleware chain
- [ ] 9.4 Ensure correct execution order: Skill → Memory
- [ ] 9.5 Implement `_execute_two_phase()` coordination method
- [ ] 9.6 Add feature flag checks for gradual rollout
- [ ] 9.7 Wire up ExecutionAnalyzer to post-execution flow
- [ ] 9.8 Add initialization logging for skill engine components

## 10. Testing

- [ ] 10.1 Create unit tests for SkillRanker BM25 and embedding logic
- [ ] 10.2 Add unit tests for SkillStore quality tracking
- [ ] 10.3 Create unit tests for sidecar ID generation and persistence
- [ ] 10.4 Add unit tests for SkillEngineMiddleware hooks
- [ ] 10.5 Create integration test for two-phase execution
- [ ] 10.6 Add integration test for full skill discovery → injection flow
- [ ] 10.7 Create tests for error resilience (component failures)
- [ ] 10.8 Add performance tests for BM25 vs embedding latency
- [ ] 10.9 Create mock tests for LLM-based skill selection
- [ ] 10.10 Add end-to-end test with real skill files

## 11. Documentation

- [ ] 11.1 Add comprehensive docstrings to all public methods
- [ ] 11.2 Create ARCHITECTURE.md explaining skill engine design
- [ ] 11.3 Update .env.example with new skill configuration options
- [ ] 11.4 Add migration guide from old skill system
- [ ] 11.5 Create example SKILL.md with keywords and backend hints
- [ ] 11.6 Document two-phase execution behavior for users
- [ ] 11.7 Add troubleshooting guide for embedding API issues
- [ ] 11.8 Update CHANGELOG.md with breaking changes

## 12. Configuration and Rollout

- [ ] 12.1 Add `skill.engine.enabled` feature flag (default false)
- [ ] 12.2 Add `skill.embedding.enabled` flag (default false for phase 1)
- [ ] 12.3 Add `skill.two_phase.enabled` flag (default false for phase 1)
- [ ] 12.4 Create monitoring metrics for skill engine performance
- [ ] 12.5 Add logging for skill selection decisions
- [ ] 12.6 Implement gradual rollout configuration
- [ ] 12.7 Create emergency disable mechanism
- [ ] 12.8 Add deprecation warnings for old skill loading paths
