## 1. Tool Models Migration

- [x] 1.1 Create `core/models/tool_models.py` with ToolSpec Pydantic model
- [x] 1.2 Create JSONSchema Pydantic model with nested property support
- [x] 1.3 Create JSONSchemaProperty Pydantic model
- [x] 1.4 Create OpenAIFunctionSchema Pydantic model
- [x] 1.5 Create OpenAIToolSchema Pydantic model
- [x] 1.6 Create MergedToolItem Pydantic model
- [x] 1.7 Add validation tests for tool models
- [x] 1.8 Update `core/models/__init__.py` exports

## 2. Config Models Migration

- [x] 2.1 Convert `core/models/config.py` to Pydantic models
- [x] 2.2 Create StateConfig Pydantic model
- [x] 2.3 Create DialogConfig Pydantic model
- [x] 2.4 Create ToolManagerConfig Pydantic model
- [x] 2.5 Create MemoryConfig Pydantic model
- [x] 2.6 Create SkillManagerConfig Pydantic model
- [x] 2.7 Create ProviderConfig Pydantic model
- [x] 2.8 Create main ConfigModel combining all sections
- [x] 2.9 Update config manager to use Pydantic models

## 3. Event Models Migration

- [x] 3.1 Create `core/models/event_models.py`
- [x] 3.2 Create EventModel base class with type and timestamp
- [x] 3.3 Create SkillEditEventModel
- [x] 3.4 Create TodoEventModel
- [x] 3.5 Create TodoItemModel with status enum
- [x] 3.6 Create ToolCallEventModel for tool start/end events
- [x] 3.7 Add event model tests
- [x] 3.8 Update event bus to support Pydantic models

## 4. Response Models Migration

- [x] 4.1 Create `core/models/response_models.py`
- [x] 4.2 Create ResultModel with ok() and error() factory methods
- [x] 4.3 Create HITLResultModel
- [x] 4.4 Create APIHealthResponse model
- [x] 4.5 Create APISendMessageResponse model
- [x] 4.6 Create APIListDialogsResponse model
- [x] 4.7 Create all remaining API response models
- [x] 4.8 Update HTTP routes to return Pydantic models

## 5. WebSocket Models Migration

- [x] 5.1 Create `core/models/websocket_models.py`
- [x] 5.2 Create WSDialogMetadataModel
- [x] 5.3 Create WSStreamingMessageModel
- [x] 5.4 Create WSDialogSnapshotModel
- [x] 5.5 Create WSSnapshotEventModel
- [x] 5.6 Create WSStreamDeltaEventModel
- [x] 5.7 Create WSErrorDetailModel and WSErrorEventModel
- [x] 5.8 Create WSStatusChangeEventModel
- [x] 5.9 Create WS Tool Call Event models
- [x] 5.10 Create WS Todo Event models
- [x] 5.11 Update WebSocket broadcaster to use Pydantic models

## 6. Stats Models Migration

- [x] 6.1 Create MemoryStatsModel
- [x] 6.2 Create SkillStatsModel
- [x] 6.3 Create EventBusStatsModel
- [x] 6.4 Update stats collection to use Pydantic models
- [x] 6.5 Update stats API endpoints

## 7. Domain Models Migration

- [x] 7.1 Review and convert `core/models/domain.py` to Pydantic
- [x] 7.2 Convert Artifact to Pydantic model
- [x] 7.3 Convert Skill to Pydantic model
- [x] 7.4 Convert SkillDefinition to Pydantic model
- [x] 7.5 Update domain model usage

## 8. DTO Models Migration

- [x] 8.1 Review and convert `core/models/dto.py` to Pydantic
- [x] 8.2 Convert ToolCall DTOs to Pydantic
- [x] 8.3 Convert Message DTOs to Pydantic
- [x] 8.4 Convert Event DTOs to Pydantic
- [x] 8.5 Convert Stats DTOs to Pydantic
- [x] 8.6 Convert Result DTOs to Pydantic
- [x] 8.7 Convert API Response DTOs to Pydantic

## 9. Types Cleanup

- [x] 9.1 Remove all TypedDict definitions from `core/models/types.py`
- [x] 9.2 Keep only exports and type aliases
- [x] 9.3 Update all imports across the codebase
- [x] 9.4 Ensure no TypedDict remains in core models

## 10. Integration Updates

- [x] 10.1 Update `core/managers/` to use Pydantic models
- [x] 10.2 Update `core/agent/` to use Pydantic models
- [x] 10.3 Update `interfaces/http/` routes
- [x] 10.4 Update `interfaces/websocket/` handlers
- [x] 10.5 Update main.py FastAPI app configuration

## 11. Testing

- [x] 11.1 Write unit tests for all Pydantic models
- [x] 11.2 Test validation errors are properly raised
- [x] 11.3 Test serialization/deserialization round-trip
- [x] 11.4 Test backward compatibility with existing JSON
- [x] 11.5 Update integration tests

## 12. Documentation

- [x] 12.1 Update CLAUDE.md with new model structure
- [x] 12.2 Create Pydantic models usage guide
- [x] 12.3 Document migration path from TypedDict
- [x] 12.4 Update API documentation

## 13. Final Verification

- [ ] 13.1 Run full test suite
- [x] 13.2 Verify no TypedDict remains in core modules
- [x] 13.3 Refactor bare dictionaries to Pydantic models in core/models/
- [ ] 13.4 Verify JSON output format unchanged
- [ ] 13.5 Performance benchmark comparison
- [ ] 13.6 Code review and cleanup
