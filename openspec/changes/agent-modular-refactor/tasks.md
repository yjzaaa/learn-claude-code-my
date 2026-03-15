## 1. Setup Project Structure

- [x] 1.1 Create `agents/plugins/` directory with `__init__.py`
- [x] 1.2 Create `agents/agents/` directory with `__init__.py`
- [x] 1.3 Create `agents/core/` directory with `__init__.py`
- [x] 1.4 Update root `agents/__init__.py` to export new modules

## 2. Core Framework (agents/core/)

- [x] 2.1 Create `builder.py` with `AgentBuilder` class
- [x] 2.2 Implement `AgentBuilder.with_base_tools()` method
- [x] 2.3 Implement `AgentBuilder.with_plugin()` method with duplicate detection
- [x] 2.4 Implement `AgentBuilder.with_monitoring()` method
- [x] 2.5 Implement `AgentBuilder.with_system()` and `with_system_append()` methods
- [x] 2.6 Implement `AgentBuilder.build()` with validation
- [x] 2.7 Add predefined builders: `simple_agent()`, `todo_agent()`, `full_agent()`

## 3. Plugin Base (agents/plugins/)

- [x] 3.1 Create `base.py` with `AgentPlugin` abstract base class
- [x] 3.2 Define `name` property abstract method
- [x] 3.3 Define `get_tools()` abstract method
- [x] 3.4 Add `on_load()` and `on_unload()` lifecycle hooks with default implementations
- [x] 3.5 Export `AgentPlugin` from `agents/plugins/__init__.py`

## 4. Todo Plugin (agents/plugins/todo.py)

- [x] 4.1 Extract `TodoManager` class from `s_full.py`
- [x] 4.2 Create `TodoPlugin` class inheriting from `AgentPlugin`
- [x] 4.3 Implement `get_tools()` returning todo tool
- [x] 4.4 Move todo tool function into plugin module
- [x] 4.5 Add unit tests for `TodoManager`
- [x] 4.6 Add unit tests for `TodoPlugin`

## 5. Task Plugin (agents/plugins/task.py)

- [x] 5.1 Extract `TaskManager` class from `s_full.py`
- [x] 5.2 Create `TaskPlugin` class inheriting from `AgentPlugin`
- [x] 5.3 Implement task tools (task_create, task_get, task_update, task_list)
- [x] 5.4 Add unit tests for `TaskManager`
- [x] 5.5 Add unit tests for `TaskPlugin`

## 6. Background Plugin (agents/plugins/background.py)

- [x] 6.1 Extract `BackgroundManager` class from `s_full.py`
- [x] 6.2 Create `BackgroundPlugin` class inheriting from `AgentPlugin`
- [x] 6.3 Implement bg_run and bg_check tools
- [x] 6.4 Ensure monitoring events are emitted (BG_TASK_*)
- [x] 6.5 Add unit tests for `BackgroundManager`
- [x] 6.6 Add unit tests for `BackgroundPlugin`

## 7. Subagent Plugin (agents/plugins/subagent.py)

- [x] 7.1 Extract `SubagentRunner` class from `s_full.py`
- [x] 7.2 Create `SubagentPlugin` class inheriting from `AgentPlugin`
- [x] 7.3 Implement subagent tool with dialog_id propagation
- [x] 7.4 Ensure monitoring events are emitted (SUBAGENT_*)
- [x] 7.5 Add unit tests for `SubagentRunner`
- [x] 7.6 Add unit tests for `SubagentPlugin`

## 8. Team Plugin (agents/plugins/team.py)

- [x] 8.1 Extract `TeammateManager` and `MessageBus` classes from `s_full.py`
- [x] 8.2 Create `TeamPlugin` class inheriting from `AgentPlugin`
- [x] 8.3 Implement team tools (spawn_teammate, list_teammates, teammate_idle, claim_work)
- [x] 8.4 Implement messaging tools (send_msg, broadcast, read_inbox)
- [x] 8.5 Add unit tests for `TeammateManager` and `MessageBus`
- [x] 8.6 Add unit tests for `TeamPlugin`

## 9. Plan Plugin (agents/plugins/plan.py)

- [x] 9.1 Extract `PlanGate` class from `s_full.py`
- [x] 9.2 Create `PlanPlugin` class inheriting from `AgentPlugin`
- [x] 9.3 Implement plan tools (submit_plan, review_plan)
- [x] 9.4 Add plan gate blocking logic
- [x] 9.5 Add unit tests for `PlanGate`
- [x] 9.6 Add unit tests for `PlanPlugin`

## 10. Agent Implementations (agents/agents/)

- [x] 10.1 Create `simple.py` with `SimpleAgent` class (base tools only)
- [x] 10.2 Create `todo.py` with `TodoAgent` extending `SimpleAgent`
- [x] 10.3 Create `subagent.py` with `SubagentAgent` extending `TodoAgent`
- [x] 10.4 Create `team.py` with `TeamAgent` extending `SubagentAgent`
- [x] 10.5 Create `full.py` with `FullAgent` extending `TeamAgent`
- [x] 10.6 Update `agents/agents/__init__.py` to export all agent classes

## 11. Backward Compatibility

- [x] 11.1 Update `s_full.py` to re-export from new modules
- [x] 11.2 Add `SFullAgent = FullAgent` alias
- [x] 11.3 Add deprecation warning to `SFullAgent` direct import
- [ ] 11.4 Verify all existing imports still work
- [ ] 11.5 Verify monitoring events still flow correctly

## 12. Integration Tests

- [x] 12.1 Test `SimpleAgent` with bash/read/write/edit tools
- [x] 12.2 Test `TodoAgent` with todo lifecycle
- [x] 12.3 Test `SubagentAgent` with subagent spawning
- [x] 12.4 Test `TeamAgent` with teammate communication
- [x] 12.5 Test `FullAgent` with all features combined
- [x] 12.6 Test `AgentBuilder` custom combinations
- [ ] 12.7 Test monitoring events for background tasks
- [ ] 12.8 Test monitoring events for subagents

## 13. Documentation

- [x] 13.1 Update `agents/plugins/__init__.py` docstring
- [x] 13.2 Update `agents/agents/__init__.py` docstring
- [x] 13.3 Update `agents/core/__init__.py` docstring
- [x] 13.4 Add migration guide from `SFullAgent` to new imports
- [x] 13.5 Add example usage for `AgentBuilder`
- [ ] 13.6 Update main project README if needed

## 14. Final Verification

- [x] 14.1 Run all existing tests to ensure no breakage
- [x] 14.2 Run all new unit tests
- [x] 14.3 Run all new integration tests
- [x] 14.4 Test backward compatibility by importing old way
- [ ] 14.5 Verify WebSocket monitoring events still work
- [ ] 14.6 Verify background task events appear in monitoring UI
