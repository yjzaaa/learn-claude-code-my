## ADDED Requirements

### Requirement: Keyword-based skill discovery
The skill discovery SHALL use keyword matching against skill metadata.

#### Scenario: Exact keyword match
- **WHEN** user message contains "finance" and a skill has keyword "finance"
- **THEN** the skill is added to matched skills list

#### Scenario: Partial keyword match
- **WHEN** user message contains "financial report" and a skill has keyword "finance"
- **THEN** the skill is matched (substring match)

#### Scenario: Multiple keyword hits
- **WHEN** user message matches multiple skills
- **THEN** all matched skills are returned with relevance scores

#### Scenario: No match
- **WHEN** user message contains no matching keywords
- **THEN** empty list is returned

### Requirement: Skill metadata source
Discovery SHALL extract keywords from SKILL.md front-matter.

#### Scenario: Keywords from front-matter
- **GIVEN** SKILL.md contains:
  ```yaml
  ---
  name: data-analysis
  keywords: [csv, excel, data, chart]
  ---
  ```
- **WHEN** discovery runs
- **THEN** keywords [csv, excel, data, chart] are extracted

#### Scenario: Fallback to name and description
- **GIVEN** SKILL.md has no keywords field
- **WHEN** discovery runs
- **THEN** skill name and description words are used as keywords

### Requirement: Relevance scoring
Discovery SHALL assign relevance scores to matched skills.

#### Scenario: Score based on keyword frequency
- **GIVEN** user message "finance finance report"
- **WHEN** skill with keyword "finance" matches
- **THEN** higher relevance score is assigned due to multiple hits

#### Scenario: Score based on recency
- **GIVEN** skill was used in previous turn
- **WHEN** it matches again
- **THEN** it receives a recency bonus in relevance score

### Requirement: Threshold filtering
Discovery SHALL filter results by minimum relevance threshold.

#### Scenario: Above threshold
- **GIVEN** threshold is 0.5 and skill scores 0.7
- **THEN** skill is included in results

#### Scenario: Below threshold
- **GIVEN** threshold is 0.5 and skill scores 0.3
- **THEN** skill is excluded from results

### Requirement: Dynamic threshold adjustment
The system SHALL adjust threshold based on conversation state.

#### Scenario: New conversation
- **GIVEN** conversation has < 3 turns
- **WHEN** discovery runs
- **THEN** lower threshold is used (more permissive)

#### Scenario: Established conversation
- **GIVEN** conversation has >= 3 turns
- **WHEN** discovery runs
- **THEN** higher threshold is used (more strict)
