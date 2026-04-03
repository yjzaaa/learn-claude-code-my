## ADDED Requirements

### Requirement: Codebase maintains zero mypy errors
The codebase SHALL pass mypy type checking with zero errors on the `core`, `interfaces`, and `main.py` targets.

#### Scenario: Running mypy on core modules
- **WHEN** a developer runs `python -m mypy core interfaces main.py --ignore-missing-imports --show-error-codes`
- **THEN** the command exits with return code 0 and produces no error-level output

### Requirement: Consistent Pydantic model usage
All manager and runtime modules SHALL use the canonical Pydantic model paths (`core.models.tool_models`, `core.models.response_models`, etc.) and SHALL NOT pass bare `dict` where a typed model is expected.

#### Scenario: Tool registration in SkillManager
- **WHEN** a skill registers a tool with parameter metadata
- **THEN** the parameters are accepted as `JSONSchema` or `dict` but internally normalized to `JSONSchema`
- **AND** no mypy assignment or argument-type errors are reported
