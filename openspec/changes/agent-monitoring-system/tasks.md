# Tasks: Agent Monitoring System

## Phase 1: Backend Infrastructure (Week 1-2)

### TASK-001: Implement MonitoringEvent Domain Model
**Priority**: P0 | **Estimated**: 4h

**Description**: Create the immutable value object for monitoring events with UUID, hierarchy support, and serialization.

**Files to Create/Modify**:
- `agents/monitoring/__init__.py`
- `agents/monitoring/domain/__init__.py`
- `agents/monitoring/domain/event.py` (new)

**Implementation Details**:
```python
@dataclass(frozen=True)
class MonitoringEvent:
    id: UUID
    type: EventType
    timestamp: datetime
    source: str
    dialog_id: str
    context_id: UUID
    parent_id: Optional[UUID]
    priority: EventPriority
    payload: dict
    metadata: dict

    def is_child_of(self, parent: 'MonitoringEvent') -> bool
    def get_duration_ms(self, since: datetime) -> int
    def to_dict(self) -> dict
    @staticmethod
    def create_child(parent, type, payload) -> 'MonitoringEvent'
```

**Acceptance Criteria**:
- [x] All properties are immutable (frozen dataclass)
- [x] UUID auto-generated if not provided
- [x] is_child_of() works correctly
- [x] to_dict() serializes all fields
- [x] create_child() factory sets parent_id correctly

---

### TASK-002: Implement EventBus Service
**Priority**: P0 | **Estimated**: 6h

**Description**: Build the async event bus with priority queue, observer pattern, and handler routing.

**Files to Create/Modify**:
- `agents/monitoring/services/__init__.py`
- `agents/monitoring/services/event_bus.py` (new)

**Implementation Details**:
- PriorityQueue for event ordering (CRITICAL=0 to LOW=3)
- Observer subscription with type filtering
- Handler routing with can_handle guards
- WebSocket integration hook
- Async processing loop

**Acceptance Criteria**:
- [x] Events processed in priority order
- [x] Observers receive only subscribed event types
- [x] Handlers only process matching events
- [x] WebSocket handler receives all events
- [x] Processing loop is cancellable

---

### TASK-003: Implement StateMachine Service
**Priority**: P0 | **Estimated**: 5h

**Description**: Create hierarchical state machine with transition guards and history tracking.

**Files to Create/Modify**:
- `agents/monitoring/services/state_machine.py` (new)

**Implementation Details**:
- AgentState enum with 10 states
- StateTransition dataclass
- Async transition with guard conditions
- Transition history with duration tracking
- Thread-safe with asyncio.Lock

**Acceptance Criteria**:
- [ ] All state transitions guarded
- [ ] Invalid transitions rejected
- [ ] History records all transitions
- [ ] Duration calculated correctly
- [ ] Thread-safe operations

---

### TASK-004: Implement BaseMonitoringBridge
**Priority**: P0 | **Estimated**: 6h

**Description**: Create abstract base class for all monitoring bridges with common functionality.

**Files to Create/Modify**:
- `agents/monitoring/bridge/__init__.py`
- `agents/monitoring/bridge/base.py` (new)

**Implementation Details**:
- IMonitoringBridge interface
- Template method pattern: initialize(), _do_initialize()
- Protected _emit() method for event creation
- State transition helpers
- Parent reference for hierarchy

**Acceptance Criteria**:
- [x] Abstract class cannot be instantiated
- [x] Subclasses implement _do_initialize()
- [x] _emit() creates events with correct context
- [x] State transitions delegate to StateMachine
- [x] Parent reference optional but supported

---

### TASK-005: Implement CompositeMonitoringBridge
**Priority**: P0 | **Estimated**: 6h

**Description**: Build composite bridge that manages child bridges for subagents and background tasks.

**Files to Create/Modify**:
- `agents/monitoring/bridge/composite.py` (new)

**Implementation Details**:
- Extends BaseMonitoringBridge
- create_subagent_bridge() factory
- create_background_task_bridge() factory
- Child lifecycle management
- Active subagent tracking

**Acceptance Criteria**:
- [x] Creates ChildMonitoringBridge correctly
- [x] Creates BackgroundTaskBridge correctly
- [x] Tracks all children in dictionary
- [x] Emits SUBAGENT_SPAWNED event
- [x] get_all_bridges() returns flat map

---

## Phase 2: Frontend Infrastructure (Week 3-4)

### TASK-006: Implement Frontend MonitoringEvent Class
**Priority**: P0 | **Estimated**: 4h

**Description**: TypeScript version of MonitoringEvent with same capabilities as backend.

**Files to Create/Modify**:
- `web/src/monitoring/__init__.ts`
- `web/src/monitoring/domain/__init__.ts`
- `web/src/monitoring/domain/Event.ts` (new)

**Implementation Details**:
- Private readonly properties
- Getter methods for all fields
- isChildOf() method
- getDurationMs() method
- fromWebSocket() factory
- createChild() factory

**Acceptance Criteria**:
- [x] Properties immutable after creation
- [x] fromWebSocket() parses backend format
- [x] createChild() sets parent_id
- [x] toJSON() serializes correctly

---

### TASK-007: Implement AgentNode Class
**Priority**: P0 | **Estimated**: 5h

**Description**: Tree node class for agent hierarchy with search and navigation methods.

**Files to Create/Modify**:
- `web/src/monitoring/domain/AgentNode.ts` (new)

**Implementation Details**:
- Tree structure (parent, children array)
- findById(), findByPredicate() search
- getDepth(), getSiblings(), getPath() navigation
- State transition methods
- Event attachment

**Acceptance Criteria**:
- [x] Tree structure maintained correctly
- [x] findById() returns correct node or undefined
- [x] getPath() returns root-to-node array
- [x] State transitions update status
- [x] Events attached and retrievable

---

### TASK-008: Implement EventDispatcher Service
**Priority**: P0 | **Estimated**: 4h

**Description**: Frontend event dispatcher mirroring backend EventBus functionality.

**Files to Create/Modify**:
- `web/src/monitoring/services/EventDispatcher.ts` (new)

**Implementation Details**:
- Observer subscription pattern
- Event routing to handlers
- No priority queue (single-threaded)
- Type-safe event handling

**Acceptance Criteria**:
- [x] Observers receive subscribed events
- [x] Handlers process matching events
- [x] Type-safe event routing
- [x] Unsubscribe works correctly

---

### TASK-009: Implement MonitoringStore
**Priority**: P0 | **Estimated**: 8h

**Description**: Core store class composing all services and managing state.

**Files to Create/Modify**:
- `web/src/monitoring/services/UIStateMachine.ts` (new)
- `web/src/monitoring/services/MetricsCollector.ts` (new)
- `web/src/monitoring/services/WebSocketEventAdapter.ts` (new)
- `web/src/monitoring/store/MonitoringStore.ts` (new)

**Implementation Details**:
- Service injection via constructor
- Event handling by type (switch statement)
- Agent hierarchy management
- Streaming content tracking
- Subscription pattern for React

**Acceptance Criteria**:
- [x] Services injected and initialized
- [x] Events routed to correct handlers
- [x] Agent hierarchy built correctly
- [x] Subscribers notified on state change
- [x] Selectors return correct values

---

### TASK-010: Implement React Integration
**Priority**: P0 | **Estimated**: 5h

**Description**: React Context Provider and hooks for monitoring store access.

**Files to Create/Modify**:
- `web/src/monitoring/react/MonitoringProvider.tsx` (new)
- `web/src/monitoring/react/hooks.ts` (new)

**Implementation Details**:
- MonitoringContext and Provider
- useMonitoringStore() hook
- useAgentHierarchy() hook
- useAgentState() hook
- useStreamingContent() hook
- useSyncExternalStore integration

**Acceptance Criteria**:
- [x] Provider renders children with context
- [x] Hooks throw outside Provider
- [x] Hooks trigger re-renders on change
- [x] useSyncExternalStore subscribes correctly

---

## Phase 3: Backend Advanced Features (Week 5)

### TASK-011: Implement BackgroundTaskBridge
**Priority**: P1 | **Estimated**: 6h

**Description**: Specialized bridge for monitoring background task execution with real-time output.

**Files to Create/Modify**:
- `agents/monitoring/bridge/background.py` (new)

**Implementation Details**:
- Subprocess management
- Output streaming handlers
- BG_TASK_* event emission
- Exit code tracking

**Acceptance Criteria**:
- [ ] Subprocess started correctly
- [ ] Output streamed in real-time
- [ ] Events emitted for all lifecycle stages
- [ ] Exit code captured

---

### TASK-012: Implement TelemetryService
**Priority**: P1 | **Estimated**: 5h

**Description**: Service for collecting and aggregating performance metrics.

**Files to Create/Modify**:
- `agents/monitoring/services/telemetry.py` (new)

**Implementation Details**:
- Token counting (input/output)
- Latency tracking
- Memory usage monitoring
- Periodic emission of METRICS events

**Acceptance Criteria**:
- [ ] Token counts accurate
- [ ] Latency calculations correct
- [ ] Metrics events emitted periodically
- [ ] Aggregation works for summaries

---

### TASK-013: Implement Event Persistence
**Priority**: P1 | **Estimated**: 4h

**Description**: JSONL-based persistence for monitoring events.

**Files to Create/Modify**:
- `agents/monitoring/persistence/__init__.py`
- `agents/monitoring/persistence/jsonl_store.py` (new)

**Acceptance Criteria**:
- [ ] Events appended to JSONL file
- [ ] File per dialog_id
- [ ] Query by time range
- [ ] Query by event type

---

### TASK-014: Integrate WebSocket Broadcasting
**Priority**: P1 | **Estimated**: 4h

**Description**: Connect EventBus to WebSocket for frontend delivery.

**Files to Create/Modify**:
- `agents/websocket/broadcast.py` (new or modify existing)

**Acceptance Criteria**:
- [x] EventBus sends to WebSocket
- [x] Events serialized correctly
- [x] Connected clients receive events
- [x] Disconnected clients cleaned up

---

## Phase 4: Frontend Advanced Features (Week 6)

### TASK-015: Implement Timeline Domain Class
**Priority**: P1 | **Estimated**: 5h

**Description**: Timeline management for event history with filtering and search.

**Files to Create/Modify**:
- `web/src/monitoring/domain/Timeline.ts` (new)

**Acceptance Criteria**:
- [x] Events sorted by timestamp
- [x] Filter by time range
- [x] Filter by event type
- [x] Filter by source

---

### TASK-016: Implement EventFilter
**Priority**: P1 | **Estimated**: 4h

**Description**: Complex query builder for event filtering.

**Files to Create/Modify**:
- `web/src/monitoring/domain/EventFilter.ts` (new)

**Acceptance Criteria**:
- [ ] Chainable filter methods
- [ ] AND/OR condition support
- [ ] Type-safe filtering

---

### TASK-017: Implement AgentHierarchy Component
**Priority**: P1 | **Estimated**: 6h

**Description**: Tree visualization component for agent hierarchy.

**Files to Create/Modify**:
- `web/src/components/monitoring/AgentHierarchy.tsx` (new)

**Acceptance Criteria**:
- [x] Tree structure renders correctly
- [x] Expand/collapse nodes
- [x] Status indicators visible
- [x] Active node highlighted

---

### TASK-018: Implement StateMachineViz Component
**Priority**: P1 | **Estimated**: 6h

**Description**: Visual representation of state machine with current state.

**Files to Create/Modify**:
- `web/src/components/monitoring/StateMachineViz.tsx` (new)

**Acceptance Criteria**:
- [x] All states displayed
- [x] Current state highlighted
- [x] Transitions animated
- [x] History visible

---

## Phase 5: Integration & Optimization (Week 7)

### TASK-019: Integrate with SFullAgent
**Priority**: P2 | **Estimated**: 6h

**Description**: Replace existing bridge with CompositeMonitoringBridge in SFullAgent.

**Files to Create/Modify**:
- `agents/agent/s_full.py`

**Acceptance Criteria**:
- [x] SFullAgent uses new bridge
- [x] All existing hooks still work
- [x] Events emitted correctly

---

### TASK-020: Migrate useWebSocket
**Priority**: P2 | **Estimated**: 5h

**Description**: Gradual migration from useWebSocket to MonitoringStore.

**Files to Create/Modify**:
- `web/src/hooks/useWebSocket.ts`

**Acceptance Criteria**:
- [ ] Backward compatibility maintained
- [ ] New features use MonitoringStore
- [ ] No regression in existing features

---

### TASK-021: Backend Performance Optimization
**Priority**: P2 | **Estimated**: 5h

**Description**: Event batching and throughput optimization.

**Acceptance Criteria**:
- [ ] Token events batched (50ms window)
- [ ] Memory usage bounded
- [ ] Throughput > 1000 events/sec

---

### TASK-022: Frontend Performance Optimization
**Priority**: P2 | **Estimated**: 5h

**Description**: Virtualization and lazy loading for large datasets.

**Acceptance Criteria**:
- [ ] Timeline virtualized for >1000 events
- [ ] RAF batching for DOM updates
- [ ] Smooth 60fps rendering

---

## Phase 6: Testing & Documentation (Week 8)

### TASK-023: Backend Unit Tests
**Priority**: P2 | **Estimated**: 8h

**Description**: Comprehensive unit tests for all backend classes.

**Files to Create/Modify**:
- `tests/monitoring/test_event.py`
- `tests/monitoring/test_event_bus.py`
- `tests/monitoring/test_state_machine.py`
- `tests/monitoring/test_bridge.py`

---

### TASK-024: Frontend Unit Tests
**Priority**: P2 | **Estimated**: 6h

**Description**: Unit tests for frontend domain and services.

**Files to Create/Modify**:
- `web/src/monitoring/__tests__/Event.test.ts`
- `web/src/monitoring/__tests__/AgentNode.test.ts`
- `web/src/monitoring/__tests__/MonitoringStore.test.ts`

---

### TASK-025: Integration Tests
**Priority**: P2 | **Estimated**: 6h

**Description**: End-to-end tests for full monitoring flow.

**Files to Create/Modify**:
- `tests/integration/test_monitoring_flow.py`

---

### TASK-026: Documentation
**Priority**: P2 | **Estimated**: 6h

**Description**: API docs and usage guides.

**Files to Create/Modify**:
- `docs/monitoring/api.md`
- `docs/monitoring/integration-guide.md`
- `docs/monitoring/best-practices.md`

---

## Summary

| Phase | Tasks | Hours | Week |
|-------|-------|-------|------|
| 1 | 5 | 27 | 1-2 |
| 2 | 5 | 26 | 3-4 |
| 3 | 4 | 19 | 5 |
| 4 | 4 | 21 | 6 |
| 5 | 4 | 21 | 7 |
| 6 | 4 | 26 | 8 |
| **Total** | **26** | **140** | **8** |

## Dependencies Graph

```
TASK-001 (Event)
    ↓
TASK-002 (EventBus) ← TASK-003 (StateMachine)
    ↓
TASK-004 (BaseBridge) ← TASK-002, TASK-003
    ↓
TASK-005 (CompositeBridge) ← TASK-004

TASK-006 (Event.ts) ← TASK-001
    ↓
TASK-007 (AgentNode) ← TASK-006
    ↓
TASK-008 (Dispatcher) ← TASK-006
    ↓
TASK-009 (Store) ← TASK-007, TASK-008
    ↓
TASK-010 (React) ← TASK-009

TASK-011 (BgBridge) ← TASK-004
TASK-012 (Telemetry) ← TASK-002
TASK-013 (Persistence) ← TASK-002
TASK-014 (WebSocket) ← TASK-002

TASK-015-018 (UI) ← TASK-010
TASK-019-020 (Integration) ← TASK-005, TASK-010
TASK-021-026 (Final) ← All above
```
