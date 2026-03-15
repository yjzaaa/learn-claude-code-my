## ADDED Requirements

### Requirement: Plan submission
The system SHALL allow agents to submit plans for approval before execution.

#### Scenario: Submit plan for approval
- **WHEN** the agent calls submit_plan(plan="1. Do X\n2. Do Y")
- **THEN** the system SHALL create a plan record with status="pending"
- **AND** assign a unique plan_id
- **AND** return {"plan_id": "...", "status": "pending"}

### Requirement: Plan review
The system SHALL support reviewing submitted plans.

#### Scenario: Approve plan
- **GIVEN** a pending plan with plan_id="plan_123"
- **WHEN** calling review_plan(plan_id="plan_123", approve=True)
- **THEN** the system SHALL update status to "approved"
- **AND** the agent SHALL be allowed to proceed

#### Scenario: Reject plan with feedback
- **GIVEN** a pending plan
- **WHEN** calling review_plan(plan_id="...", approve=False, feedback="Too risky")
- **THEN** the system SHALL update status to "rejected"
- **AND** store the feedback for the agent to see

### Requirement: Plan gate blocking
The system SHALL block agent execution on unapproved plans if enabled.

#### Scenario: Block on pending plan
- **GIVEN** plan approval gate is enabled
- **AND** a critical action requires plan approval
- **WHEN** attempting to execute without approved plan
- **THEN** the system SHALL raise PlanApprovalRequired exception
- **AND** provide the pending plan_id

#### Scenario: Allow execution after approval
- **GIVEN** a plan with status="approved"
- **WHEN** attempting to execute the planned action
- **THEN** the system SHALL allow execution to proceed

### Requirement: Plan persistence
The system SHALL persist plans across sessions.

#### Scenario: Plan survives restart
- **GIVEN** a pending plan exists
- **WHEN** the agent restarts
- **THEN** the plan SHALL still be available
- **AND** maintain its pending status
