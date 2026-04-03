## ADDED Requirements

### Requirement: Audit tool identifies bare JSON type annotations
The audit tool SHALL identify all Python type annotations that use bare dict types instead of Pydantic models.

#### Scenario: Finding Dict[str, Any] annotations
- **WHEN** the audit tool scans a Python file
- **THEN** it SHALL flag any occurrence of `Dict[str, Any]` in type annotations

#### Scenario: Finding bare dict return types
- **WHEN** the audit tool scans a Python file
- **THEN** it SHALL flag function return types annotated as `-> dict` or `-> Dict[...]`

#### Scenario: Finding bare dict parameters
- **WHEN** the audit tool scans a Python file
- **THEN** it SHALL flag function parameters with type `dict` or `Dict[...]` without Pydantic model constraints

### Requirement: Audit tool uses configurable regex patterns
The audit tool SHALL use configurable regular expression patterns to identify problematic code patterns.

#### Scenario: Using default patterns
- **WHEN** the audit tool runs without configuration
- **THEN** it SHALL use built-in regex patterns to identify bare JSON usage

#### Scenario: Custom pattern configuration
- **WHEN** the audit tool runs with a custom configuration file
- **THEN** it SHALL use the user-defined regex patterns in addition to or instead of defaults

### Requirement: Audit tool generates detailed reports
The audit tool SHALL generate a report listing all files, line numbers, and specific violations found.

#### Scenario: Report format
- **WHEN** the audit completes
- **THEN** it SHALL output a report with file path, line number, matched text, and suggested fix

#### Scenario: Exit code on violations
- **WHEN** violations are found
- **THEN** the audit tool SHALL exit with non-zero code

## MODIFIED Requirements

None

## REMOVED Requirements

None
