## 1. Project Structure Setup

- [x] 1.1 Create `backend/infrastructure/event_bus/` directory
- [x] 1.2 Create `backend/infrastructure/agent_queue/` directory
- [x] 1.3 Create `backend/infrastructure/websocket_buffer/` directory

## 2. QueuedEventBus Implementation

- [x] 2.1 Define `QueuedEventBus` class wrapping existing EventBus
- [x] 2.2 Add `AsyncQueue[BaseEvent]` as internal buffer
- [x] 2.3 Implement `emit()` with enqueue and backpressure
- [x] 2.4 Implement consumer loop with configurable concurrency
- [x] 2.5 Add `start()` and `shutdown()` lifecycle methods
- [x] 2.6 Ensure API compatibility with existing EventBus

## 3. AgentTaskQueue Implementation

- [x] 3.1 Define `AgentTask` dataclass with priority field
- [x] 3.2 Define `AgentTaskQueue` class with AsyncQueue
- [x] 3.3 Implement `submit(task)` method
- [x] 3.4 Implement `asyncio.Semaphore` for concurrency control
- [x] 3.5 Add worker loop to consume and execute tasks
- [x] 3.6 Implement priority queue support (if using PriorityQueue)
- [x] 3.7 Add `get_stats()` for queue metrics

## 4. WebSocketMessageBuffer Implementation

- [x] 4.1 Define `WebSocketMessageBuffer` class
- [x] 4.2 Add per-client `AsyncQueue[WebSocketMessage]`
- [x] 4.3 Implement `send_buffered(message, strategy)` with strategy selection
- [x] 4.4 Implement blocking wait strategy
- [x] 4.5 Implement drop-on-full strategy
- [x] 4.6 Implement timeout strategy
- [x] 4.7 Add consumer loop to send messages via WebSocket

## 5. Testing

- [x] 5.1 Test QueuedEventBus basic emit/subscribe
- [x] 5.2 Test QueuedEventBus backpressure under load
- [x] 5.3 Test AgentTaskQueue task submission
- [x] 5.4 Test AgentTaskQueue concurrency limit
- [x] 5.5 Test AgentTaskQueue priority ordering
- [x] 5.6 Test WebSocketMessageBuffer basic buffering
- [x] 5.7 Test WebSocketMessageBuffer full queue strategies

## 6. Integration

- [x] 6.1 Add exports to infrastructure `__init__.py` files
- [x] 6.2 Create usage examples in module docstrings
- [x] 6.3 Document configuration options
- [x] 6.4 Verify imports work correctly

## 7. Documentation

- [x] 7.1 Add QueuedEventBus usage example
- [x] 7.2 Add AgentTaskQueue usage example
- [x] 7.3 Add WebSocketMessageBuffer usage example
- [x] 7.4 Create migration guide from EventBus to QueuedEventBus
