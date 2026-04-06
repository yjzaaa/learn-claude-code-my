# Skill Engine Architecture

## Overview

Skill Engine is a modular system for intelligent skill discovery, ranking, and execution in the Agent Runtime. It implements a hybrid BM25 + Embedding ranking algorithm, two-phase execution strategy, and quality tracking mechanisms.

## Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      DeepAgentRuntime                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  SkillEngineMiddleware                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │ SkillRanker │  │ SkillStore  │  │ExecutionAnalyzer│  │  │
│  │  │  (BM25 +    │  │  (Quality   │  │   (Pattern      │  │  │
│  │  │ Embedding)  │  │  Tracking)  │  │  Recognition)   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────┼──────────────────────────────┐  │
│  │     TwoPhaseExecutionMixin│TwoPhaseSkillStoreMixin       │  │
│  │                           │                               │  │
│  │  Phase 1: Skill-guided    │  - Records completions        │  │
│  │  Phase 2: Tool-fallback   │  - Records fallbacks          │  │
│  │                           │  - Quality metrics            │  │
│  └───────────────────────────┴──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Core Modules

### 1. SkillRanker (`backend/infrastructure/services/skill_ranker.py`)

**Purpose**: Hybrid ranking of skills using BM25 + Embedding

**Algorithm**:
1. **BM25 Pre-filtering**: Quickly narrow down candidates (when >10 skills)
2. **Embedding Re-ranking**: Semantic similarity using text-embedding-3-small
3. **Local Caching**: Embeddings cached to `.skill_embedding_cache/skill_embeddings_v1.pkl`

**Key Features**:
- Token overlap fallback when rank-bm25 not available
- Automatic cache invalidation based on file mtime
- Configurable embedding model

### 2. SkillStore (`backend/infrastructure/persistence/skill_store.py`)

**Purpose**: Quality tracking and metrics persistence

**Metrics Tracked**:
- `total_selections`: Times LLM selected the skill
- `total_applied`: Times skill was applied to conversation
- `total_completions`: Times skill completed task successfully
- `total_fallbacks`: Times skill triggered fallback

**Storage**: JSONL format (`skill_quality.jsonl`), append-only writes

**Filtering Rules**:
- Skills selected >=2 times but never completed → Filtered
- Skills with >50% fallback rate after 2+ applications → Filtered

### 3. SkillIDSidecar (`backend/infrastructure/services/skill_id_sidecar.py`)

**Purpose**: Persistent skill ID management

**ID Format**:
- Imported: `{name}__imp_{uuid8}` (e.g., `finance__imp_a3f2b1c9`)
- Evolved: `{name}__v{gen}_{uuid8}` (e.g., `finance__v2_b4e5d6f7`)

**Storage**: `.skill_id` file in each skill directory

### 4. SkillEngineMiddleware (`backend/infrastructure/runtime/deep/middleware/skill_engine.py`)

**Purpose**: Core middleware for skill discovery and injection

**Execution Order**:
```
1. SkillEngineMiddleware.abefore_model() → Discover & inject skills
2. MemoryMiddleware.abefore_model()      → Load relevant memories
3. LLM Call
4. SkillEngineMiddleware.aafter_model()  → Track execution
```

**Backend-Aware Prompt Injection**:
- Detects available backends from tool configuration
- Generates dynamic hints based on available tools
- Replaces `{baseDir}` placeholders with absolute paths
- Formats skills with consistent headers and separators

### 5. ExecutionAnalyzer (`backend/infrastructure/services/execution_analyzer.py`)

**Purpose**: Execution result analysis and improvement suggestions

**Error Patterns**:
- `missing_tool`: Tool not found errors
- `parameter_error`: Invalid parameters
- `timeout`: Execution timeouts
- `permission_denied`: Access denied errors
- `file_not_found`: Missing files
- `syntax_error`: Code syntax errors
- `dependency_error`: Missing dependencies

**Analysis Modes**:
- Sync analysis: Blocking, immediate results
- Async analysis: Non-blocking, background processing
- LLM-based: Deep analysis using LLM (optional)

### 6. TwoPhaseExecutionMixin (`backend/infrastructure/runtime/deep/mixins/two_phase.py`)

**Purpose**: Two-phase execution strategy

**Flow**:
```
Phase 1: Skill-guided Execution
    ├── Take workspace snapshot
    ├── Execute with skills
    └── If success → Return result
    └── If failure → Cleanup workspace → Phase 2

Phase 2: Tool-fallback Execution
    └── Execute without skills
```

**Workspace Cleanup**:
- Records pre-execution file state
- Removes files created during failed Phase 1
- Preserves original files

## Data Flow

### Skill Discovery and Injection

```
User Query
    ↓
SkillEngineMiddleware.abefore_model()
    ↓
SkillRanker.hybrid_rank(query, skills)
    ├── BM25 pre-filter (if >10 skills)
    └── Embedding re-rank
    ↓
Apply quality filter (SkillStore)
    ↓
Select top N skills (max_select=2)
    ↓
Build context injection
    ├── Add "# Active Skills" header
    ├── Add backend hints
    ├── Add resource access tips
    └── Format each skill section
    ↓
Inject into system message
```

### Two-Phase Execution

```
execute_with_two_phase(dialog_id, message)
    ↓
Phase 1: _execute_skill_phase()
    ├── Take workspace snapshot
    ├── Execute agent with skills
    └── Record result
    ↓
Phase 1 Success?
    ├── Yes → Record completion → Return result
    └── No → Record fallback → Cleanup → Phase 2
    ↓
Phase 2: _execute_tool_fallback_phase()
    ├── Execute agent without skills
    └── Record result
    ↓
Return result with metrics
```

## Configuration

### SkillEngineConfig (`backend/infrastructure/runtime/deep/middleware/skill_engine_config.py`)

```yaml
skill:
  enabled: true                    # Master switch
  max_select: 2                    # Max skills to inject
  prefilter_threshold: 10          # BM25 threshold
  
  embedding:
    enabled: true                  # Enable embedding ranking
    model: "openai/text-embedding-3-small"
    max_chars: 12000               # Text truncation
    cache_dir: ".skill_embedding_cache"
    
  two_phase:
    enabled: true                  # Enable two-phase execution
    cleanup_workspace: true        # Cleanup on fallback
    full_iterations_on_fallback: true
    
  quality:
    enabled: true                  # Enable quality tracking
    data_file: "skill_quality.jsonl"
    filter_problematic: true       # Auto-filter bad skills
    never_completed_threshold: 2
    fallback_ratio_threshold: 0.5
    
  evolution:
    enabled: false                 # Auto-evolution (Phase 2)
    auto_fix: false                # Generate FIX skills
    auto_derive: false             # Extract DERIVED skills
```

## Integration Points

### DeepAgentRuntime Integration

```python
class DeepAgentRuntime(
    ...,
    TwoPhaseExecutionMixin,
    TwoPhaseSkillStoreMixin,
    ...
):
    def _init_skill_engine(self):
        # Initialize components based on config
        self._skill_ranker = SkillRanker(...)
        self._skill_store = SkillStore(...)
        self._execution_analyzer = ExecutionAnalyzer(...)
```

### Middleware Chain Order

```python
# Correct order: Skill → Memory
middlewares = [
    SkillEngineMiddleware(...),   # Injects skills first
    MemoryMiddleware(...),        # Then adds memories
]
```

## File Locations

| Component | Path |
|-----------|------|
| Types | `backend/domain/models/agent/skill_engine_types.py` |
| Config | `backend/infrastructure/runtime/deep/middleware/skill_engine_config.py` |
| Ranker | `backend/infrastructure/services/skill_ranker.py` |
| Store | `backend/infrastructure/persistence/skill_store.py` |
| Sidecar | `backend/infrastructure/services/skill_id_sidecar.py` |
| Middleware | `backend/infrastructure/runtime/deep/middleware/skill_engine.py` |
| Analyzer | `backend/infrastructure/services/execution_analyzer.py` |
| TwoPhase | `backend/infrastructure/runtime/deep/mixins/two_phase.py` |
| SkillStore Mixin | `backend/infrastructure/runtime/deep/mixins/two_phase_skill_store.py` |

## Testing

Test files are located in `tests/`:

| Test | Path |
|------|------|
| SkillRanker | `tests/infrastructure/test_skill_ranker.py` |
| SkillStore | `tests/infrastructure/test_skill_store.py` |
| SkillIDSidecar | `tests/infrastructure/test_skill_id_sidecar.py` |
| ExecutionAnalyzer | `tests/infrastructure/test_execution_analyzer.py` |
| Backend-Aware Injection | `tests/runtime/test_backend_aware_injection.py` |
| Integration | `tests/runtime/test_skill_engine_integration.py` |
| Two-Phase Execution | `tests/runtime/test_two_phase_execution.py` |

Run tests:
```bash
pytest tests/infrastructure/test_execution_analyzer.py -v
pytest tests/runtime/test_backend_aware_injection.py -v
pytest tests/runtime/test_skill_engine_integration.py -v
```
