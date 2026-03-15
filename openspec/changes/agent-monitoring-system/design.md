# Design: Agent Monitoring System

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MONITORING SYSTEM ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         Frontend (TypeScript/React)                   │  │
│  │                                                                       │  │
│  │   MonitoringStore ◄───── Domain Models (Event, AgentNode)             │  │
│  │        │                                                              │  │
│  │        ├── EventDispatcher (Observer pattern)                         │  │
│  │        ├── UIStateMachine (State management)                          │  │
│  │        └── MetricsCollector (Performance tracking)                    │  │
│  │                                                                       │  │
│  │   React Layer:                                                        │  │
│  │        ├── MonitoringProvider (Context)                               │  │
│  │        └── Hooks (useAgentState, useHierarchy, etc.)                  │  │
│  │                                                                       │  │
│  └───────────────────────────────┬───────────────────────────────────────┘  │
│                                  │ WebSocket                                 │
│  ┌───────────────────────────────┴───────────────────────────────────────┐  │
│  │                          Backend (Python)                               │  │
│  │                                                                       │  │
│  │   CompositeMonitoringService (Facade)                                 │  │
│  │        │                                                              │  │
│  │        ├── EventBus (Priority queue, async)                           │  │
│  │        ├── StateMachine (Hierarchical states)                         │  │
│  │        └── TelemetryService (Metrics aggregation)                     │  │
│  │                                                                       │  │
│  │   Bridge Layer:                                                       │  │
│  │        ├── CompositeMonitoringBridge (Parent)                         │  │
│  │        │        ├── ChildMonitoringBridge (Subagents)                 │  │
│  │        │        └── BackgroundTaskBridge (Async tasks)                │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Backend Design

### Domain Models

#### MonitoringEvent (Value Object)
- Immutable frozen dataclass
- UUID-based identification
- Parent-child relationship support
- Priority-based queuing
- Full serialization support

#### EventType (Enum)
- AGENT_STARTED/STOPPED/ERROR/PAUSED/RESUMED
- MESSAGE_START/DELTA/COMPLETE, REASONING_DELTA
- TOOL_CALL_START/END/ERROR, TOOL_RESULT
- SUBAGENT_SPAWNED/STARTED/PROGRESS/COMPLETED/FAILED
- BG_TASK_QUEUED/STARTED/PROGRESS/COMPLETED/FAILED
- STATE_TRANSITION/ENTER/EXIT
- TOKEN_USAGE/MEMORY_USAGE/LATENCY_METRIC

#### AgentState (Enum)
IDLE → INITIALIZING → THINKING → (TOOL_CALLING | SUBAGENT_RUNNING | BACKGROUND_TASKS) → COMPLETED

### Services

#### EventBus (Observer Pattern)
- PriorityQueue for event ordering
- Observer subscription management
- Handler routing with guards
- WebSocket integration hook

#### StateMachine
- State transition rules with guards
- Transition history tracking
- Async state change support
- Time-in-state tracking

### Bridge Hierarchy

```
IMonitoringBridge (Interface)
    △
    │
BaseMonitoringBridge (Abstract)
    │       Template methods: initialize(), _emit(), _transition_state()
    │
    ├── CompositeMonitoringBridge
    │       Creates: ChildMonitoringBridge, BackgroundTaskBridge
    │       Manages: child lifecycle, event propagation
    │
    ├── ChildMonitoringBridge
    │       Tracks: subagent execution
    │       Reports: to parent bridge
    │
    └── BackgroundTaskBridge
            Manages: subprocess execution
            Streams: real-time output
```

## Frontend Design

### Domain Models

#### MonitoringEvent (Class)
- Immutable properties with getters
- isChildOf() for hierarchy
- getDurationMs() for timing
- fromWebSocket() factory
- createChild() factory

#### AgentNode (Class)
- Tree structure (parent/children)
- findById(), findByPredicate() search
- getDepth(), getPath() navigation
- transitionState(), complete(), fail() lifecycle
- attachEvent(), getEvents() event association

### Store Architecture

#### MonitoringStore
- Composes: EventDispatcher, UIStateMachine, MetricsCollector
- Manages: _rootAgent, _events Map, streaming content
- Handles: event routing by type
- Supports: subscription pattern

#### State Selection Pattern
```typescript
// Selectors for fine-grained reactivity
const hierarchy = useSelector(store => store.getAgentHierarchy());
const agentState = useSelector(store => store.getAgentState());
const streaming = useSelector(store => store.getStreamingContent());
```

## Design Patterns Applied

| Pattern | Location | Purpose |
|---------|----------|---------|
| Observer | EventBus ↔ Observers | Decoupled event handling |
| Strategy | EventHandler | Pluggable processors |
| Composite | CompositeBridge | Hierarchy management |
| Template Method | MonitoringService | Initialization flow |
| Factory | Event.createChild() | Hierarchical events |
| Singleton | EventBus instance | Global coordination |

## SOLID Compliance

- **S**: Each class has single responsibility
- **O**: New handlers/strategies without modifying existing code
- **L**: ChildBridge substitutable for BaseBridge
- **I**: IMonitoringBridge exposes only necessary methods
- **D**: Bridges depend on EventBus abstraction

## Data Flow

```
Agent Action → Bridge._emit() → EventBus.emit() → PriorityQueue
                                                    ↓
WebSocketHandler ← dispatch() ← Event Processing
       ↓
Frontend receives → EventDispatcher.dispatch() → Store._handleEvent()
                                                       ↓
Subscribers notified ← useSyncExternalStore ← Store state update
```

## Key Decisions

1. **Priority Queue**: Critical events (errors, state changes) processed before low-priority (token deltas)

2. **Immutable Events**: Events are value objects, no mutation after creation

3. **Bridge Hierarchy**: Parent-child relationship mirrors agent execution hierarchy

4. **Async Everything**: All event processing is async to prevent blocking

5. **Subscription Pattern**: Frontend uses selectors for fine-grained reactivity

## File Structure

```
agents/monitoring/
├── domain/
│   ├── event.py
│   └── metrics.py
├── services/
│   ├── event_bus.py
│   ├── state_machine.py
│   └── telemetry.py
├── bridge/
│   ├── base.py
│   ├── composite.py
│   ├── child.py
│   └── background.py
└── persistence/
    └── jsonl_store.py

web/src/monitoring/
├── domain/
│   ├── Event.ts
│   └── AgentNode.ts
├── services/
│   ├── EventDispatcher.ts
│   ├── UIStateMachine.ts
│   ├── MetricsCollector.ts
│   └── WebSocketEventAdapter.ts
├── store/
│   └── MonitoringStore.ts
└── react/
    ├── MonitoringProvider.tsx
    └── hooks.ts
```

## Testing Strategy

- **Unit**: Individual classes in isolation
- **Integration**: Service interactions
- **E2E**: Full frontend-backend flow
- **Performance**: Event throughput, memory usage
