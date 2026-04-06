# Skill Engine Migration Guide

## Overview

This guide helps you migrate from the old skill system to the new Skill Engine with BM25 + Embedding ranking, two-phase execution, and quality tracking.

## What's New

### New Features

1. **BM25 + Embedding Hybrid Ranking**: Skills are now ranked using a combination of BM25 text matching and semantic embedding similarity
2. **Two-Phase Execution**: Skills are tried first, with automatic fallback to tool-only execution on failure
3. **Quality Tracking**: Automatic tracking of skill success/failure rates with problematic skill filtering
4. **Backend-Aware Prompt Injection**: Dynamic prompt generation based on available tools
5. **Skill ID Sidecar**: Persistent skill IDs using `.skill_id` files

### Breaking Changes

None. The new system is fully backward compatible. Old skill loading continues to work.

## Migration Steps

### Step 1: Update Configuration (Optional)

Add Skill Engine configuration to your `config.yaml`:

```yaml
skill:
  enabled: true                    # Master switch
  max_select: 2                    # Max skills to inject per query
  prefilter_threshold: 10          # Use BM25 when >10 skills
  
  embedding:
    enabled: false                 # Start with false for Phase 1
    model: "openai/text-embedding-3-small"
    cache_dir: ".skill_embedding_cache"
    
  two_phase:
    enabled: false                 # Start with false for Phase 1
    cleanup_workspace: true
    
  quality:
    enabled: true                  # Safe to enable immediately
    data_file: "skill_quality.jsonl"
    filter_problematic: false      # Start with false, enable after monitoring
```

### Step 2: Install Dependencies (Optional)

For optimal BM25 ranking:

```bash
pip install rank-bm25
```

For embedding ranking (when enabled):

```bash
pip install openai
```

### Step 3: Generate Skill IDs

Skill IDs are automatically generated on first load. To pre-generate:

```python
from backend.infrastructure.services.skill_id_sidecar import _read_or_create_skill_id
from pathlib import Path

skills_dir = Path("skills")
for skill_dir in skills_dir.iterdir():
    if skill_dir.is_dir():
        skill_id, is_new = _read_or_create_skill_dir(skill_dir, skill_dir.name)
        print(f"{skill_dir.name}: {skill_id} (new={is_new})")
```

### Step 4: Enable Gradually

#### Phase 1: BM25 Only (Default)

```yaml
skill:
  enabled: true
  embedding:
    enabled: false
  two_phase:
    enabled: false
```

Monitor logs for:
- Skill ranking behavior
- Quality metrics accumulation

#### Phase 2: Enable Two-Phase Execution

```yaml
skill:
  enabled: true
  two_phase:
    enabled: true
    cleanup_workspace: true
```

Monitor for:
- Fallback rates
- Workspace cleanup effectiveness

#### Phase 3: Enable Embedding (When Ready)

```yaml
skill:
  enabled: true
  embedding:
    enabled: true
```

Requires:
- OpenAI API key configured
- Sufficient skills (>10) to benefit from embedding

### Step 5: Enable Quality Filtering

After collecting enough metrics (1-2 weeks):

```yaml
skill:
  quality:
    enabled: true
    filter_problematic: true
```

## Rollback

If issues occur, disable immediately:

```yaml
skill:
  enabled: false
```

Or set environment variable:

```bash
export SKILL_ENGINE_ENABLED=false
```

## Troubleshooting

### Skills Not Being Selected

**Check**:
1. Skill Engine enabled in config
2. Skills have proper SKILL.md with frontmatter
3. Quality filtering not removing all skills

**Debug**:
```python
from backend.infrastructure.runtime.deep import DeepAgentRuntime

runtime = DeepAgentRuntime("test")
runtime._init_skill_engine()

components = runtime.get_skill_engine_components()
print(f"Enabled: {components['enabled']}")
print(f"Ranker: {components['ranker']}")
```

### Embedding API Errors

**Symptom**: `Failed to generate embedding` errors

**Solution**:
1. Disable embedding: `skill.embedding.enabled: false`
2. Check API key: `config.api_keys.openai`
3. Verify model name format: `openai/text-embedding-3-small`

### High Fallback Rates

**Symptom**: Most tasks fall back to Phase 2

**Causes**:
1. Skills not relevant to queries
2. Skill quality issues
3. Phase 1 iteration limit too low

**Solutions**:
1. Review skill descriptions and keywords
2. Check quality metrics: `skill_quality.jsonl`
3. Increase `max_iterations_phase1`

### Workspace Cleanup Issues

**Symptom**: Files not cleaned up after fallback

**Check**:
1. `cleanup_workspace: true` in config
2. Proper permissions on skill directories
3. Check logs for cleanup errors

## Monitoring

### Key Metrics

Monitor these in `skill_quality.jsonl`:

```bash
# Total records
wc -l skill_quality.jsonl

# Problematic skills
python -c "
from backend.infrastructure.persistence.skill_store import SkillStore
store = SkillStore()
for skill in store.get_problematic_skills():
    print(f'{skill.skill_id}: {skill.fallback_rate:.1%} fallback')
"
```

### Logs to Watch

```bash
# Skill ranking
grep "SkillRanker" logs/app.log

# Two-phase execution
grep "TwoPhaseExecution" logs/app.log

# Quality tracking
grep "SkillStore" logs/app.log
```

## Best Practices

### Skill Development

1. **Use descriptive names**: Helps BM25 matching
2. **Write clear descriptions**: Used for embedding generation
3. **Include keywords**: In SKILL.md frontmatter
4. **Test with real queries**: Verify ranking quality

### Example SKILL.md

```markdown
---
name: data-analysis
description: Analyze datasets using pandas and generate insights. Keywords: csv, excel, statistics, visualization
---

# Data Analysis Skill

Use this skill when users ask about:
- Analyzing CSV/Excel files
- Statistical calculations
- Data visualization
- Report generation

## Available Tools

- `read_file`: Load data files
- `pandas`: Data manipulation
- `matplotlib`: Visualization

## Workflow

1. Load data with `read_file`
2. Explore with pandas
3. Generate visualizations
4. Summarize findings
```

### Performance Optimization

1. **Embedding Cache**: Automatically managed in `.skill_embedding_cache/`
2. **BM25 Threshold**: Adjust `prefilter_threshold` based on skill count
3. **Max Skills**: Keep `max_select` low (2-3) to prevent prompt bloat

## API Changes

### New Methods

```python
# DeepAgentRuntime
runtime._init_skill_engine()           # Initialize components
runtime.is_skill_engine_enabled()      # Check if enabled
runtime.get_skill_engine_components()  # Get all components

# TwoPhaseExecutionMixin
runtime.configure_two_phase(config)
runtime.execute_with_two_phase(dialog_id, message)
runtime.get_two_phase_metrics()

# TwoPhaseSkillStoreMixin
runtime.configure_skill_store(store, task_id)
runtime.set_active_skills(skill_ids)
```

### Deprecated (Still Work)

```python
# Old skill loading (still works)
runtime._load_skill_scripts()  # Now part of SkillManager
```

## Support

For issues or questions:
1. Check logs in `logs/app.log`
2. Review `skill_quality.jsonl` for metrics
3. Verify configuration in `config.yaml`
4. Run tests: `pytest tests/runtime/test_skill_engine*.py -v`
