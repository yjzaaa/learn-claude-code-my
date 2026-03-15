# Proposal: Agent Monitoring System

## What

Build a comprehensive monitoring system that provides full transparency into agent operations. The system will enable real-time monitoring of:

- Agent lifecycle events (start, stop, error, pause, resume)
- Message streaming with content and reasoning deltas
- Tool call execution with arguments and results
- Subagent spawning and hierarchy tracking
- Background task execution with real-time output
- State machine transitions
- Performance metrics (tokens, latency, memory)

## Why

Currently, the agent system operates as a black box from the frontend perspective. Users cannot see:

1. **What subagents are spawned** - No visibility into task decomposition
2. **Background task progress** - Long-running commands show no output until completion
3. **State transitions** - Cannot track agent's internal state changes
4. **Performance metrics** - No insight into token usage or latency

This monitoring system will provide complete observability, enabling:
- Better debugging and troubleshooting
- Performance optimization insights
- Educational value for understanding agent behavior
- Real-time user feedback during long operations

## Success Criteria

| Criterion | How to Measure |
|-----------|---------------|
| Real-time event streaming | Events appear in UI within 100ms of backend emission |
| Complete subagent hierarchy | Parent-child relationships correctly visualized |
| Background task output | Terminal-like real-time output streaming |
| State machine visualization | Current state and transition history displayed |
| Performance metrics | Token count and latency accurately tracked |

## Scope

### In Scope
- Backend monitoring infrastructure (EventBus, StateMachine, Bridges)
- Frontend Store and React integration
- Agent hierarchy visualization
- Real-time streaming content display
- Background task monitoring
- Performance metrics collection

### Out of Scope (Future)
- Historical data querying and replay
- Alerting and notification system
- Multi-dialog correlation
- External metrics export (Prometheus, etc.)

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Event flooding | Medium | High | Implement priority queue and batching |
| Memory growth | Medium | Medium | Event retention limits, pagination |
| WebSocket reconnection | High | Medium | Robust reconnection with state sync |
| Performance overhead | Medium | Medium | Async processing, optional monitoring |

## Alternatives Considered

### Alternative 1: Simple Logging
Just add more logging statements.

**Rejected**: Logging is not real-time and doesn't provide structured data for UI visualization.

### Alternative 2: Direct WebSocket from Agent
Agent directly sends WebSocket messages.

**Rejected**: Tight coupling, harder to maintain, no centralized event management.

### Alternative 3: Use Existing StateManagedBridge
Extend current bridge implementation.

**Rejected**: Current design mixes concerns. Clean separation enables better testing and future extensions.

## Decision

Proceed with full OOP architecture as designed in [design.md](design.md).

## Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1 | 1-2 weeks | Backend infrastructure |
| Phase 2 | 1-2 weeks | Frontend infrastructure |
| Phase 3 | 1 week | Backend advanced features |
| Phase 4 | 1 week | Frontend advanced features |
| Phase 5 | 1 week | Integration and optimization |
| Phase 6 | 1 week | Testing and documentation |

**Total: 6-8 weeks**
