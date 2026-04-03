## 1. Infrastructure Layer Interfaces

- [x] 1.1 Create `core/infra/interfaces.py` with `ILLMProvider`, `IEventBus`, `IStateStorage`
- [x] 1.2 Update `EventBus` to implement `IEventBus`
- [x] 1.3 Update `LiteLLMProvider` to implement `ILLMProvider`
- [x] 1.4 Create `FileStorage` implementing `IStateStorage` (or adapt existing storage)

## 2. Capability Layer Interfaces

- [x] 2.1 Create `core/capabilities/interfaces.py` with manager interfaces
- [ ] 2.2 Update `DialogManager` to implement `IDialogManager`
- [ ] 2.3 Update `ToolManager` to implement `IToolManager`
- [ ] 2.4 Update `SkillManager` to implement `ISkillManager`
- [ ] 2.5 Update `MemoryManager` to implement `IMemoryManager`

## 3. Runtime Layer Interfaces

- [x] 3.1 Create `core/runtime/interfaces.py` with `IAgentRuntime`, `IAgentRuntimeFactory`, `AgentEvent`
- [x] 3.2 Move existing `AgentEvent` from `core/types/` to Pydantic model in runtime interfaces
- [ ] 3.3 Refactor `SimpleRuntime` constructor to accept interfaces
- [ ] 3.4 Refactor `DeepAgentRuntime` constructor to accept interfaces
- [ ] 3.5 Remove duplicate `create_dialog` from `DeepAgentRuntime` (inherited from base)

## 4. Bridge Layer Interfaces

- [x] 4.1 Create `core/bridge/interfaces.py` with `IAgentRuntimeBridge`, `IWebSocketBroadcaster`
- [x] 4.2 Refactor `AgentRuntimeBridge` to implement `IAgentRuntimeBridge`
- [ ] 4.3 Create `WebSocketBroadcaster` implementing `IWebSocketBroadcaster`
- [x] 4.4 Remove direct `_runtime` access from `main.py` routes

## 5. Dependency Injection Container

- [x] 5.1 Create `core/container.py` with `SimpleContainer` class
- [ ] 5.2 Register infrastructure layer singletons (EventBus, StateStorage)
- [ ] 5.3 Register capability layer factories (DialogManager, ToolManager, etc.)
- [ ] 5.4 Register runtime factory
- [ ] 5.5 Register bridge as singleton with injected dependencies

## 6. AgentRuntimeFactory Rewrite

- [x] 6.1 Create new `AgentRuntimeFactory` implementing `IAgentRuntimeFactory`
- [x] 6.2 Register `SimpleRuntime` under key "simple"
- [x] 6.3 Register `DeepAgentRuntime` under key "deep"
- [x] 6.4 Support `config` parameter in `create()` method
- [ ] 6.5 Remove old `AgentFactory` (keep only if backward compatibility needed)

## 7. Main.py Integration

- [x] 7.1 Update `lifespan()` to use new AgentRuntimeFactory
- [x] 7.2 Remove direct access to `agent_bridge._runtime`
- [x] 7.3 Add `AGENT_TYPE` environment variable usage in factory
- [x] 7.4 Verify `AGENT_TYPE=deep` path works

## 8. Model Cleanup

- [ ] 8.1 Remove duplicate imports from `core/models/__init__.py`
- [ ] 8.2 Update deprecated Pydantic `class Config` to `ConfigDict`
- [ ] 8.3 Verify no circular imports introduced

## 9. Testing

- [ ] 9.1 Create `tests/runtime/test_factory.py` - Factory creation tests
- [ ] 9.2 Create `tests/container/test_di.py` - Container resolution tests
- [ ] 9.3 Create `tests/integration/test_layer_isolation.py` - Verify no direct concrete imports
- [ ] 9.4 Add test for `AGENT_TYPE=deep` runtime creation
- [ ] 9.5 Verify all existing tests still pass

## 10. Documentation

- [ ] 10.1 Update CLAUDE.md with new architecture diagram
- [ ] 10.2 Add "依赖注入" section to CLAUDE.md
- [ ] 10.3 Document how to add new Runtime type
- [ ] 10.4 Update API docs if any public interface changed
