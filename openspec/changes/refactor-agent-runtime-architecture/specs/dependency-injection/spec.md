## ADDED Requirements

### Requirement: Container manages singleton instances
The DI Container SHALL manage singleton instances for stateful services.

#### Scenario: Singleton returns same instance
- **GIVEN** `IEventBus` registered as singleton
- **WHEN** resolving `IEventBus` twice
- **THEN** both calls SHALL return the same instance

#### Scenario: Factory returns new instances
- **GIVEN** `IDialogManager` registered as factory
- **WHEN** resolving `IDialogManager` twice
- **THEN** each call SHALL return a new instance

### Requirement: Container supports interface-to-implementation mapping
The Container SHALL allow registering an implementation for an interface.

#### Scenario: Register and resolve interface
- **GIVEN** `IEventBus` interface registered with `EventBus` implementation
- **WHEN** resolving `IEventBus`
- **THEN** it SHALL return an `EventBus` instance
- **AND** the instance SHALL satisfy `IEventBus` interface

### Requirement: Container supports constructor injection
The Container SHALL automatically inject dependencies into constructors.

#### Scenario: Auto-inject dependencies
- **GIVEN** `DialogManager` constructor requires `IEventBus` and `IStateStorage`
- **AND** both dependencies are registered in container
- **WHEN** resolving `IDialogManager`
- **THEN** the returned instance SHALL have its dependencies injected
- **AND** the dependencies SHALL be the registered implementations

### Requirement: Container provides bridge initialization
The Container SHALL provide a pre-configured `IAgentRuntimeBridge` instance.

#### Scenario: Get configured bridge
- **GIVEN** all dependencies (Factory, Broadcasters, Managers) are registered
- **WHEN** requesting `IAgentRuntimeBridge` from container
- **THEN** it SHALL return a fully configured `AgentRuntimeBridge`
- **AND** the bridge SHALL have its factory dependency injected
