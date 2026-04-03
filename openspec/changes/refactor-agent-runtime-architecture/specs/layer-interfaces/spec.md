## ADDED Requirements

### Requirement: Infrastructure layer exposes interface module
The infrastructure layer SHALL expose all its interfaces via `core/infra/interfaces.py`.

#### Scenario: Import infrastructure interfaces
- **WHEN** importing from `core.infra.interfaces`
- **THEN** it SHALL export `ILLMProvider`, `IEventBus`, `IStateStorage`
- **AND** all interfaces SHALL be abstract base classes

### Requirement: Capability layer exposes interface module
The capability layer SHALL expose all its interfaces via `core/capabilities/interfaces.py`.

#### Scenario: Import capability interfaces
- **WHEN** importing from `core.capabilities.interfaces`
- **THEN** it SHALL export `IDialogManager`, `IToolManager`, `ISkillManager`, `IMemoryManager`
- **AND** all manager interfaces SHALL define the full public API

### Requirement: Runtime layer exposes interface module
The runtime layer SHALL expose all its interfaces via `core/runtime/interfaces.py`.

#### Scenario: Import runtime interfaces
- **WHEN** importing from `core.runtime.interfaces`
- **THEN** it SHALL export `IAgentRuntime`, `IAgentRuntimeFactory`
- **AND** it SHALL export `AgentEvent` model
- **AND** `AgentEvent` SHALL use Pydantic BaseModel

### Requirement: Bridge layer exposes interface module
The bridge layer SHALL expose all its interfaces via `core/bridge/interfaces.py`.

#### Scenario: Import bridge interfaces
- **WHEN** importing from `core.bridge.interfaces`
- **THEN** it SHALL export `IAgentRuntimeBridge`, `IWebSocketBroadcaster`
- **AND** `IAgentRuntimeBridge` SHALL define all bridge operations

### Requirement: Implementations depend on interfaces only
All implementation classes SHALL only depend on interfaces from lower layers.

#### Scenario: SimpleRuntime dependencies
- **GIVEN** `SimpleRuntime` implementation
- **WHEN** inspecting its constructor
- **THEN** it SHALL only accept `IDialogManager`, `IToolManager`, `IProviderRegistry` interfaces
- **AND** it SHALL NOT import any concrete manager class

#### Scenario: AgentRuntimeBridge dependencies
- **GIVEN** `AgentRuntimeBridge` implementation
- **WHEN** inspecting its constructor
- **THEN** it SHALL only accept `IAgentRuntimeFactory` and `IWebSocketBroadcaster`
- **AND** it SHALL NOT import any concrete runtime class
