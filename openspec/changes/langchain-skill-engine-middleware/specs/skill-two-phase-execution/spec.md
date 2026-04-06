## ADDED Requirements

### Requirement: Skill-First phase execution
The system SHALL attempt skill-guided execution first when skills are available.

#### Scenario: Skills selected
- **GIVEN** skills are discovered and selected for the task
- **WHEN** execute() is called
- **THEN** GroundingAgent runs with skill prompts injected

#### Scenario: No skills available
- **GIVEN** no skills match the task
- **WHEN** execute() is called
- **THEN** skip Phase 1 and go directly to tool-only execution

### Requirement: Phase success detection
The system SHALL correctly detect skill phase success or failure.

#### Scenario: Successful completion
- **GIVEN** skill-guided execution completes
- **WHEN** status is "success"
- **THEN** result is returned immediately, no fallback triggered

#### Scenario: Incomplete status
- **GIVEN** skill-guided execution ends with status "incomplete"
- **WHEN** max iterations reached
- **THEN** fallback to tool-only phase is triggered

#### Scenario: Error status
- **GIVEN** skill-guided execution throws exception
- **WHEN** error is caught
- **THEN** fallback to tool-only phase is triggered

### Requirement: Workspace cleanup on fallback
The system SHALL clean workspace before fallback execution.

#### Scenario: Snapshot before Phase 1
- **GIVEN** Phase 1 is about to start
- **WHEN** workspace is initialized
- **THEN** snapshot of existing files is captured

#### Scenario: Cleanup on fallback
- **GIVEN** Phase 1 failed and fallback is triggered
- **WHEN** cleanup executes
- **THEN** files created during Phase 1 are deleted
- **AND** original files are preserved

#### Scenario: Directory removal
- **GIVEN** Phase 1 created new directories
- **WHEN** cleanup executes
- **THEN** directories and their contents are recursively removed

### Requirement: Tool-Fallback phase execution
The system SHALL execute tool-only phase when skill phase fails.

#### Scenario: Fallback triggered
- **GIVEN** Phase 1 failed and cleanup completed
- **WHEN** Phase 2 starts
- **THEN** skill context is cleared
- **AND** full iteration budget is allocated

#### Scenario: Clean state
- **GIVEN** Phase 2 is executing
- **WHEN** agent checks available tools
- **THEN** no skill-specific tools are visible

#### Scenario: Fallback result
- **GIVEN** Phase 2 completes
- **WHEN** result is returned
- **THEN** response includes "fallback: true" marker

### Requirement: Budget allocation
The system SHALL allocate fair iteration budgets.

#### Scenario: Phase 1 success budget
- **GIVEN** max_iterations = 20
- **WHEN** Phase 1 executes
- **THEN** it receives full budget of 20 iterations

#### Scenario: Phase 2 fallback budget
- **GIVEN** Phase 1 used 10 iterations and failed
- **WHEN** Phase 2 starts
- **THEN** it receives full budget of 20 iterations (not 10)

### Requirement: Execution tracking
The system SHALL track both phases in metrics.

#### Scenario: Phase metrics
- **GIVEN** two-phase execution completes
- **WHEN** metrics are recorded
- **THEN** phase1_iterations, phase2_iterations, and fallback_triggered are stored

#### Scenario: Skill attribution
- **GIVEN** fallback was triggered
- **WHEN** final result is analyzed
- **THEN** active_skills field still shows Phase 1 skills for analysis
