## ADDED Requirements

### Requirement: API spec documents REST endpoints
The API specification SHALL document all REST API endpoints with methods, paths, and request/response formats.

#### Scenario: REST API documentation complete
- **WHEN** a developer reads api_spec.md
- **THEN** they see documented endpoints for /api/dialogs, /api/dialogs/{id}/messages, /health, etc.

### Requirement: API spec documents WebSocket protocol
The API specification SHALL document the WebSocket event protocol.

#### Scenario: WebSocket protocol clarity
- **WHEN** a developer reads WebSocket section
- **THEN** they understand event types (dialog:snapshot, stream:delta, status:change), message formats, and connection flow

### Requirement: API spec includes DTO definitions
The API specification SHALL include all Data Transfer Object definitions.

#### Scenario: DTO definitions documented
- **WHEN** a developer reads DTO section
- **THEN** they see field names, types, and descriptions for all request/response objects

### Requirement: API spec documents authentication
The API specification SHALL document authentication mechanisms if any.

#### Scenario: Authentication documented
- **WHEN** a developer reads authentication section
- **THEN** they understand how API access is controlled (or note if public)
