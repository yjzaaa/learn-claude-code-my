## Context

当前项目使用 **AgentMiddleware** 模式扩展 Agent 功能，如 `ClaudeCompressionMiddleware` 实现了四层压缩机制。系统采用 Clean Architecture 分层架构（Domain -> Application -> Infrastructure -> Interfaces），通过 EventBus 进行事件驱动通信。

参考 free-code 的记忆系统实现，我们需要将记忆功能以 **AgentMiddleware** 方式嵌入现有架构，同时支持**混合存储模式**（服务端 Postgres 为主存储 + 客户端 IndexedDB 为缓存），保持：
1. **Clean Architecture** 依赖方向向内
2. **Pydantic 优先** 所有数据模型使用 Pydantic
3. **事件驱动** 通过 EventBus 解耦
4. **AgentMiddleware 风格** 与 ClaudeCompressionMiddleware 一致
5. **隐私优先** 用户可选择数据存储位置

## Goals / Non-Goals

**Goals:**
- 实现四层记忆类型存储（user/feedback/project/reference）
- 通过 **AgentMiddleware** 集成到 Runtime，与 ClaudeCompressionMiddleware 架构一致
- 支持记忆的自动提取和智能检索
- 实现**混合存储架构**：服务端 Postgres（主存储）+ 客户端 IndexedDB（缓存）
- 支持隐私模式（用户可选择本地优先）
- 实现记忆老化管理（新鲜度追踪）
- 支持多用户场景（用户数据隔离）

**Non-Goals:**
- 向量嵌入和语义搜索（未来扩展，本次仅关键词匹配）
- 团队记忆功能（依赖 TEAMMEM 标志，本次仅个人记忆）
- 跨设备实时同步（Phase 2）
- 记忆可视化 Web UI
- 自动压缩/归档旧记忆

## Decisions

### 1. AgentMiddleware vs Mixin vs Service
**Decision**: 使用 **AgentMiddleware** 集成到 Runtime
**Rationale**: 
- **与现有架构一致**: `ClaudeCompressionMiddleware` 已使用此模式，可链式组合多个中间件
- **非侵入式**: 不需要修改 DeepAgentRuntime 类，通过配置注册中间件
- **标准接口**: 通过 `before_model` / `abefore_model` / `aafter_model` 标准生命周期钩子操作 AgentState
- **可组合性**: 可同时启用 MemoryMiddleware + ClaudeCompressionMiddleware + 其他中间件
- **Alternative - Mixin**: 侵入性强，需要修改 Runtime 类继承链
- **Alternative - Service**: 需要显式调用，无法自动拦截查询生命周期

**使用方式**:
```python
runtime.middleware = [
    MemoryMiddleware(project_path=".", llm_provider=llm),
    ClaudeCompressionMiddleware(model=llm),
]
```

### 2. 混合存储架构（Postgres + IndexedDB）
**Decision**: 采用三层存储架构
**Rationale**:

| 层级 | 存储 | 用途 | 隐私级别 |
|------|------|------|---------|
| **L1 缓存** | 客户端内存 | 当前会话记忆 | 完全私有 |
| **L2 缓存** | IndexedDB | 最近 20 条 + 离线队列 | 完全私有 |
| **主存储** | Postgres | 完整记忆历史 | 服务端可见 |

**优点**:
- **性能**: 客户端缓存减少 API 调用，加速读取
- **离线支持**: IndexedDB 支持离线写入，联网后同步
- **隐私灵活**: 用户可选择是否同步到服务端
- **多用户支持**: Postgres 天然支持 user_id 隔离
- **与现有架构兼容**: 复用已有的 Postgres 容器

**Alternative - 纯文件系统**: 不支持多用户，性能差
**Alternative - 纯客户端**: AgentMiddleware 无法访问，需要重构架构

### 3. 自动提取触发时机
**Decision**: 在 `aafter_model` 钩子中自动触发（main agent 响应完成后）
**Rationale**:
- 与 free-code 的 extractMemories 机制一致
- AgentMiddleware 提供标准的 `aafter_model` 生命周期钩子
- 完整的对话上下文可用于提取
- 使用 `asyncio.create_task()` 后台执行，避免阻塞主流程
- **Alternative**: 实时提取会中断对话流，手动提取增加用户负担

### 4. 记忆检索时机
**Decision**: 在 `abefore_model` 钩子中加载相关记忆（从服务端 Postgres）
**Rationale**:
- Agent 运行在服务端，直接访问 Postgres（主存储）
- 在 LLM 调用前拦截，可修改 AgentState['messages']
- 基于最后一条用户消息作为查询关键词
- 注入系统提示词，让模型在生成响应时考虑记忆上下文
- **客户端缓存**: 浏览器端维护最近 20 条缓存，减少重复请求

### 5. 记忆老化策略
**Decision**: 软老化（附加警告提示）而非硬删除
**Rationale**:
- 保留历史信息供参考
- 让用户/模型自行判断信息可靠性
- 实现简单（仅比较时间戳）
- **Alternative**: 自动删除可能丢失有价值的历史上下文

### 6. Repository 模式（支持多存储后端）
**Decision**: 实现 Repository 抽象，支持多种存储后端
**Rationale**:
- Clean Architecture 要求依赖抽象
- 当前实现 PostgresRepository（服务端）
- 未来可添加 IndexedDBRepository（纯客户端模式）
- 便于测试（可 Mock Repository）

## Middleware 架构详解

### MemoryMiddleware 结构

```python
class MemoryMiddleware(AgentMiddleware):
    """记忆系统中间件 - 加载和提取记忆"""
    
    def __init__(self, user_id: str, project_path: str, db_session_factory, auto_extract: bool = True):
        self.user_id = user_id  # 多用户隔离
        self.project_path = project_path
        self.repo = PostgresMemoryRepository(db_session_factory, user_id)
        self.service = MemoryService(self.repo)
        self.auto_extract = auto_extract
    
    # ═══════════════════════════════════════════════════════════
    # 查询前：从 Postgres 加载记忆
    # ═══════════════════════════════════════════════════════════
    
    async def abefore_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        """在 LLM 调用前加载相关记忆（从服务端 Postgres）"""
        messages = state.get("messages", [])
        
        # 获取最后一条用户消息作为查询
        last_user_msg = self._get_last_user_message(messages)
        if not last_user_msg:
            return None
        
        # 从 Postgres 检索相关记忆（带 user_id 过滤）
        memories = await self.service.get_relevant_memories(
            user_id=self.user_id,
            project_path=self.project_path,
            query=last_user_msg,
            limit=5
        )
        
        if not memories:
            return None
        
        # 构建记忆提示词并插入
        memory_prompt = self._build_memory_prompt(memories)
        modified_messages = self._inject_memory_prompt(messages, memory_prompt)
        
        return {"messages": modified_messages}
    
    # ═══════════════════════════════════════════════════════════
    # 查询后：提取新记忆并写入 Postgres
    # ═══════════════════════════════════════════════════════════
    
    async def aafter_model(self, state: AgentState, runtime: Runtime, output: Any) -> dict | None:
        """在 LLM 响应后提取记忆并写入服务端"""
        if not self.auto_extract:
            return None
        
        # 检查是否是最终响应（无工具调用）
        if self._has_pending_tool_calls(output):
            return None
        
        # 后台异步提取并写入 Postgres
        asyncio.create_task(self._extract_and_save_memories(state.get("messages", [])))
        return None
    
    async def _extract_and_save_memories(self, messages: list):
        """提取并保存记忆到 Postgres"""
        extractor = MemoryExtractor(self.llm)
        new_memories = await extractor.extract_from_conversation(messages)
        
        for memory in new_memories:
            await self.service.create_memory(
                user_id=self.user_id,
                project_path=self.project_path,
                type=memory.type,
                content=memory.content
            )
```

### 与 ClaudeCompressionMiddleware 的协作

```
用户查询
    ↓
[MemoryMiddleware.abefore_model]      ← 从 Postgres 加载记忆
    ↓
[ClaudeCompressionMiddleware.abefore_model]  ← 压缩消息
    ↓
LLM 调用
    ↓
[ClaudeCompressionMiddleware.aafter_model]   ← 保存 transcript
    ↓
[MemoryMiddleware.aafter_model]       ← 提取记忆写入 Postgres
    ↓
返回响应
```

### 客户端缓存架构（浏览器端）

```typescript
// 浏览器端记忆管理器
class ClientMemoryManager {
  private db: IDBDatabase;
  private syncQueue: MemorySyncQueue;
  
  async getMemory(id: string): Promise<Memory | null> {
    // 1. 优先读取 IndexedDB 缓存
    const cached = await this.db.get('memories', id);
    if (cached) return cached;
    
    // 2. 缓存未命中，请求服务端 API
    const memory = await api.getMemory(id);
    
    // 3. 回填缓存
    await this.db.put('memories', memory);
    return memory;
  }
  
  async saveMemory(memory: Memory): Promise<void> {
    // 1. 立即写入 IndexedDB（本地优先）
    await this.db.put('memories', memory);
    
    // 2. 加入同步队列
    await this.syncQueue.add({
      type: 'SAVE',
      data: memory,
      timestamp: Date.now()
    });
    
    // 3. 后台同步到服务端
    this.flushSyncQueue();
  }
  
  // 离线支持
  async getRecentMemories(limit: number = 20): Promise<Memory[]> {
    // 直接从 IndexedDB 读取，无需网络
    return await this.db.getAll('memories', null, limit);
  }
}
```

### 同步协议

```typescript
// 同步队列管理
interface SyncOperation {
  id: string;
  type: 'SAVE' | 'UPDATE' | 'DELETE';
  data: Memory;
  timestamp: number;
  retryCount: number;
}

class MemorySyncManager {
  async flushQueue(): Promise<void> {
    const pending = await this.syncQueue.getPending();
    
    for (const op of pending) {
      try {
        switch (op.type) {
          case 'SAVE':
            await api.createMemory(op.data);
            break;
          case 'UPDATE':
            await api.updateMemory(op.data.id, op.data);
            break;
          case 'DELETE':
            await api.deleteMemory(op.data.id);
            break;
        }
        await this.syncQueue.markCompleted(op.id);
      } catch (error) {
        await this.syncQueue.incrementRetry(op.id);
        if (op.retryCount >= 3) {
          await this.syncQueue.markFailed(op.id);
        }
      }
    }
  }
}
```

## 混合存储数据流

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              浏览器 (Browser)                                │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │   IndexedDB      │◄──►│  Memory Cache    │◄──►│  Sync Manager    │      │
│  │   (L2 缓存)      │    │  (L1 内存)       │    │  (离线队列)      │      │
│  │                  │    │                  │    │                  │      │
│  │ • 最近 20 条记忆 │    │ • 当前会话       │    │ • 待同步操作     │      │
│  │ • 用户偏好设置   │    │ • 快速访问       │    │ • 冲突解决       │      │
│  │ • 离线写入队列   │    │                  │    │                  │      │
│  └────────┬─────────┘    └──────────────────┘    └────────┬─────────┘      │
│           │                                               │                 │
│           │  1. 读取优先本地缓存                          │                 │
│           │  2. 缓存未命中则请求 API                      │ 3. 后台同步    │
│           │                                               │                 │
│  ┌────────▼───────────────────────────────────────────────┴─────────┐      │
│  │                     Export / Import / Backup                      │      │
│  │  • 导出为 Markdown 文件（用户完全掌控）                          │      │
│  │  • 从文件导入记忆                                                │      │
│  │  • 端到端加密备份（可选）                                        │      │
│  └───────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTP API / WebSocket
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              服务端 (Server)                                 │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │  Postgres        │◄──►│  Memory Service  │◄──►│  Sync API        │      │
│  │  (主存储)         │    │  (业务逻辑)       │    │  (HTTP/WS)       │      │
│  │                  │    │                  │    │                  │      │
│  │ • user_id 隔离   │    │ • 权限验证       │    │ • 批量同步       │      │
│  │ • ACID 事务      │    │ • 记忆提取       │    │ • 冲突检测       │      │
│  │ • 备份/恢复      │    │ • 老化管理       │    │ • 实时推送       │      │
│  └──────────────────┘    └────────┬─────────┘    └──────────────────┘      │
│                                   │                                         │
│                                   ▼                                         │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │              AgentMiddleware (MemoryMiddleware)               │          │
│  │  • abefore_model: 从 Postgres 加载记忆（带 user_id 过滤）    │          │
│  │  • aafter_model:  提取记忆 → 写入 Postgres                   │          │
│  │  • 不直接访问客户端存储（通过 API 间接访问）                  │          │
│  └──────────────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 隐私模式配置

```python
# 用户可选择存储策略
class MemoryStorageConfig:
    """记忆存储配置"""
    
    # 存储模式
    mode: Literal["server", "local", "hybrid"] = "hybrid"
    
    # 同步策略（hybrid 模式下）
    sync_strategy: Literal["realtime", "periodic", "manual"] = "periodic"
    
    # 加密选项
    encryption: bool = False  # 端到端加密
    
    # 保留策略
    local_retention_days: int = 30  # 本地保留天数
    server_retention_days: int = 365  # 服务端保留天数
```

**模式说明**:
- `server`: 标准模式，所有记忆同步到服务端 Postgres
- `local`: 隐私模式，仅存储在浏览器 IndexedDB，不同步到服务端
- `hybrid`: 混合模式，本地优先，按需同步到服务端

## Risks / Trade-offs

**[Risk] 服务端数据隐私**（用户担心服务端可见记忆内容）
→ **Mitigation**: 支持端到端加密；提供 local 模式（完全本地存储）；用户可选择不同步敏感记忆

**[Risk] 客户端数据丢失**（IndexedDB 被清理）
→ **Mitigation**: 定期自动备份到服务端；支持导出/导入；重要记忆提示用户确认备份

**[Risk] 同步冲突**（多设备同时修改）
→ **Mitigation**: 时间戳-based 冲突解决（last-write-wins）；用户手动合并界面（未来）

**[Risk] 离线时 Agent 无法访问完整记忆**
→ **Mitigation**: IndexedDB 缓存最近 20 条，覆盖大部分场景；离线提示用户

**[Risk] 数据一致性**（客户端和服务端数据不一致）
→ **Mitigation**: 同步队列 + 重试机制；定期全量同步；冲突检测和解决策略

**[Trade-off] 隐私 vs 便利性**
- local 模式：完全隐私，但无法跨设备，Agent 只能访问最近缓存
- server 模式：便利（跨设备、完整历史），但服务端可见数据
- hybrid 模式：平衡，但需要处理同步复杂性

## Migration Plan

**部署步骤**:
1. **Phase 1**: 实现服务端 Postgres 存储 + AgentMiddleware
2. **Phase 2**: 实现客户端 IndexedDB 缓存 + 同步机制
3. **Phase 3**: 添加隐私模式配置和端到端加密

**代码变更**:
```python
# 数据库迁移
alembic revision --autogenerate -m "add memories table"

# Runtime 注册
runtime.middleware = [
    MemoryMiddleware(
        user_id=current_user.id,
        project_path=project_path,
        db_session_factory=session_factory
    ),
    ClaudeCompressionMiddleware(model=llm),
]
```

**Rollback Strategy**:
- 从 middleware 列表中移除 MemoryMiddleware 即可禁用
- 支持导出记忆为 Markdown 文件，用户可随时带走数据
- 设置环境变量 `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` 禁用自动提取
- 不影响现有对话和功能

## Open Questions

1. **加密方案**: 使用哪种端到端加密方案（OpenPGP, libsodium, Web Crypto API）？
2. **同步频率**: hybrid 模式下自动同步的频率（实时/5分钟/手动）？
3. **冲突解决**: 复杂冲突场景下是否需要用户手动合并界面？
4. **存储限制**: 是否需要限制 IndexedDB 存储大小（浏览器配额限制）？
5. **记忆分享**: 是否支持将特定记忆分享给其他用户（保持隐私）？
6. **Middleware 顺序**: MemoryMiddleware 是否应该在 CompressionMiddleware 之前？
