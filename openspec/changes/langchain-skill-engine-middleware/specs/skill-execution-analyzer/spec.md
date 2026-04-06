## ADDED Requirements

### Requirement: Execution result analysis
The ExecutionAnalyzer SHALL analyze task execution results.

#### Scenario: Success analysis
- **GIVEN** task completed successfully with skills
- **WHEN** analysis runs
- **THEN** it records success=True and identifies success patterns

#### Scenario: Failure analysis
- **GIVEN** task failed during skill-guided phase
- **WHEN** analysis runs
- **THEN** it records success=False and identifies error patterns

#### Scenario: Fallback analysis
- **GIVEN** fallback was triggered
- **WHEN** analysis runs
- **THEN** it records fallback_triggered=True and analyzes root cause

### Requirement: Error pattern recognition
The analyzer SHALL identify common error patterns.

#### Scenario: Tool not found
- **GIVEN** error message contains "tool not found"
- **WHEN** pattern matching runs
- **THEN** it identifies pattern as "missing_tool"

#### Scenario: Parameter validation error
- **GIVEN** error involves invalid parameters
- **WHEN** pattern matching runs
- **THEN** it identifies pattern as "parameter_error"

#### Scenario: Timeout error
- **GIVEN** error is timeout-related
- **WHEN** pattern matching runs
- **THEN** it identifies pattern as "timeout"

#### Scenario: Permission denied
- **GIVEN** error is permission-related
- **WHEN** pattern matching runs
- **THEN** it identifies pattern as "permission_denied"

### Requirement: Improvement suggestion
The analyzer SHALL suggest skill improvements.

#### Scenario: Missing tool guidance
- **GIVEN** error pattern is "missing_tool"
- **WHEN** suggestion is generated
- **THEN** it suggests "Add explicit tool availability check"

#### Scenario: Parameter clarification
- **GIVEN** error pattern is "parameter_error"
- **WHEN** suggestion is generated
- **THEN** it suggests "Clarify parameter format with examples"

#### Scenario: Step refinement
- **GIVEN** error occurred at specific step
- **WHEN** suggestion is generated
- **THEN** it identifies step number and suggests refinement

### Requirement: Evolution candidacy
The analyzer SHALL flag skills for evolution.

#### Scenario: Repeat failure
- **GIVEN** skill failed 3+ times with same pattern
- **WHEN** analysis runs
- **THEN** candidate_for_evolution=True is set

#### Scenario: Success pattern
- **GIVEN** novel success pattern detected
- **WHEN** analysis runs
- **THEN** candidate_for_capture=True is set

### Requirement: LLM-based analysis
The analyzer SHALL use LLM for deep analysis.

#### Scenario: Recording available
- **GIVEN** recording directory with conversation log
- **WHEN** LLM analysis runs
- **THEN** conversation is analyzed for root cause

#### Scenario: Tool executions
- **GIVEN** tool execution history
- **WHEN** analysis runs
- **THEN** failed tool calls are identified and analyzed

#### Scenario: Context summary
- **GIVEN** full execution context
- **WHEN** analysis completes
- **THEN** it produces brief_plan summary and skill_effectiveness assessment

### Requirement: Metadata recording
The analyzer SHALL persist analysis results.

#### Scenario: Analysis record
- **GIVEN** analysis is complete
- **WHEN** recording runs
- **THEN** result is written to metadata.json

#### Scenario: Task linkage
- **GIVEN** analysis is recorded
- **WHEN** record is stored
- **THEN** it is linked to task_id for traceability

### Requirement: Non-blocking execution
The analyzer SHALL not block main flow.

#### Scenario: Async analysis
- **GIVEN** task completes
- **WHEN** analysis starts
- **THEN** it runs asynchronously without delaying response

#### Scenario: Analysis failure
- **GIVEN** analysis throws exception
- **WHEN** error is caught
- **THEN** it is logged but does not affect task result
