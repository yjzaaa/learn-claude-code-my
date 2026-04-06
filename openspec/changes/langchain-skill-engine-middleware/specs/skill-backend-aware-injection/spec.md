## ADDED Requirements

### Requirement: Backend scope awareness
The middleware SHALL know available backends.

#### Scenario: Backend discovery
- **GIVEN** GroundingClient has registered providers
- **WHEN** middleware initializes
- **THEN** it receives list of available backends (shell, mcp, gui, etc.)

#### Scenario: Scope configuration
- **GIVEN** agent config specifies backend_scope = ["shell", "mcp"]
- **WHEN** middleware builds injection
- **THEN** only shell and mcp backends are mentioned

### Requirement: Dynamic tool hints
The prompt SHALL mention only available tools.

#### Scenario: Shell available
- **GIVEN** "shell" is in backend scope
- **WHEN" prompt is built
- **THEN** it includes "Use shell_agent for running scripts"

#### Scenario: MCP available
- **GIVEN** "mcp" is in backend scope
- **WHEN** prompt is built
- **THEN** it includes "Use MCP tools for external integrations"

#### Scenario: GUI available
- **GIVEN** "gui" is in backend scope
- **WHEN** prompt is built
- **THEN" it includes GUI-specific guidance

#### Scenario: Backend not available
- **GIVEN** "web" is not in backend scope
- **WHEN** prompt is built
- **THEN** no web-related guidance is included

### Requirement: Resource access guidance
The prompt SHALL include resource access tips.

#### Scenario: File operations
- **WHEN** prompt is built
- **THEN** it mentions "Use read_file / list_dir / write_file for file operations"

#### Scenario: Skill directory reference
- **GIVEN** skill is at /path/to/skills/finance/
- **WHEN** prompt references resources
- **THEN** it uses "relative to the skill directory listed under each skill heading"

### Requirement: {baseDir} placeholder replacement
The middleware SHALL replace {baseDir} placeholders.

#### Scenario: Placeholder in skill body
- **GIVEN** SKILL.md contains "See {baseDir}/scripts/helper.py"
- **WHEN** prompt is injected
- **THEN** {baseDir} is replaced with actual skill directory path

#### Scenario: Absolute path
- **GIVEN** placeholder is replaced
- **WHEN** agent reads the prompt
- **THEN** path is absolute and resolvable

### Requirement: Active skills header
The prompt SHALL have consistent header format.

#### Scenario: Header structure
- **WHEN** skill context is built
- **THEN** it starts with "# Active Skills"

#### Scenario: Usage instructions
- **WHEN** header is present
- **THEN** it includes "How to use skills" section with bullet points

#### Scenario: Skill separator
- **GIVEN** multiple skills are injected
- **WHEN" they are concatenated
- **THEN** they are separated by "---\n\n"

### Requirement: Skill metadata inclusion
Each skill SHALL include metadata in prompt.

#### Scenario: Skill ID
- **GIVEN** skill has ID "finance__imp_a3f2b1c9"
- **WHEN** skill section is built
- **THEN** header is "### Skill: finance__imp_a3f2b1c9"

#### Scenario: Skill directory
- **GIVEN" skill is at /path/to/skills/finance/
- **WHEN** skill section is built
- **THEN** it includes "**Skill directory**: `/path/to/skills/finance/`"

#### Scenario: Full content
- **GIVEN** SKILL.md body contains instructions
- **WHEN** skill section is built
- **THEN** full body content (without frontmatter) is included
