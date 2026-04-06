## ADDED Requirements

### Requirement: Core metrics tracking
The SkillStore SHALL track four core metrics per skill.

#### Scenario: Selection tracking
- **GIVEN** skill is selected by LLM for a task
- **WHEN** selection is recorded
- **THEN** total_selections counter increments by 1

#### Scenario: Application tracking
- **GIVEN** skill is actually injected into agent context
- **WHEN** application is recorded
- **THEN** total_applied counter increments by 1

#### Scenario: Completion tracking
- **GIVEN** skill-guided execution succeeds
- **WHEN** completion is recorded
- **THEN** total_completions counter increments by 1

#### Scenario: Fallback tracking
- **GIVEN** skill-guided execution fails and triggers fallback
- **WHEN** fallback is recorded
- **THEN** total_fallbacks counter increments by 1

### Requirement: Quality-based filtering
The system SHALL filter out low-quality skills.

#### Scenario: Never-completed filter
- **GIVEN** skill has selections >= 2 and completions == 0
- **WHEN** skill selection list is prepared
- **THEN** skill is filtered out with warning log

#### Scenario: High-fallback filter
- **GIVEN** skill has applied >= 2 and fallbacks/applied > 0.5
- **WHEN** skill selection list is prepared
- **THEN** skill is filtered out with warning log

#### Scenario: Quality annotation
- **GIVEN** skill passes quality filters
- **WHEN** selection prompt is built
- **THEN** quality metrics are included ("success 6/8 = 75%")

### Requirement: Data persistence
The SkillStore SHALL persist quality data.

#### Scenario: JSONL format
- **GIVEN** metrics are recorded
- **WHEN** data is persisted
- **THEN** format is JSONL (one JSON object per line)

#### Scenario: Data loading
- **GIVEN** application restarts
- **WHEN** SkillStore initializes
- **THEN** it loads historical metrics from JSONL file

#### Scenario: Aggregation
- **GIVEN** multiple records exist for same skill
- **WHEN** metrics are queried
- **THEN** counters are summed across all records

### Requirement: Per-task recording
The SkillStore SHALL record per-task skill usage.

#### Scenario: Task association
- **GIVEN** task is executed with skills
- **WHEN** execution completes
- **THEN** task_id is associated with skill_ids in metadata

#### Scenario: Result tracking
- **GIVEN** task used skills
- **WHEN** result is recorded
- **THEN** status (success/fallback/failure) is stored with skill_ids

### Requirement: Metrics API
The SkillStore SHALL provide query interface.

#### Scenario: Get skill summary
- **WHEN** get_summary(skill_id) is called
- **THEN** it returns dict with all four counters

#### Scenario: List active skills
- **WHEN** get_active_skills() is called
- **THEN** it returns skills sorted by completion rate

#### Scenario: Get problematic skills
- **WHEN** get_problematic_skills() is called
- **THEN** it returns skills matching filter criteria
