# 记忆系统架构嵌入设计

基于 free-code 记忆系统分析，为当前项目设计的嵌入架构方案。

---

## 1. 架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Interfaces 层                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  MemoryCommands          /memory, /remember                            ││
│  │  MemoryWebSocketHandler  实时记忆同步                                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Application 层                                   │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │   MemoryService     │  │  MemoryExtractor    │  │  MemoryRetriever    │  │
│  │   (记忆管理服务)     │  │  (记忆提取器)        │  │  (记忆检索器)        │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                      MemoryEvents (领域事件)                            ││
│  │   MemoryCreatedEvent / MemoryUpdatedEvent / MemoryExtractedEvent        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                Domain 层                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │      Memory         │  │    MemoryType       │  │  MemoryRepository   │  │
│  │    (实体模型)        │  │    (枚举)            │  │    (接口)            │  │
│  │   - id, type        │  │  - USER             │  │  - save()           │  │
│  │   - content         │  │  - FEEDBACK         │  │  - findById()       │  │
│  │   - metadata        │  │  - PROJECT          │  │  - search()         │  │
│  │   - created_at      │  │  - REFERENCE        │  │  - listByType()     │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Infrastructure 层                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    MemoryMixin (添加到 Runtime)                         ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  ││
│  │  │ MemoryInitializer│  │MemoryExtractor │  │    MemoryRetriever      │  ││
│  │  │   - initDirs()   │  │ - extract()    │  │  - semanticSearch()    │  ││
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    Repository Implementations                           ││
│  │  ┌─────────────────────────┐  ┌─────────────────────────────────────────┐││
│  │  │ FileSystemMemoryRepo    │  │      (未来: VectorMemoryRepo)           │││
│  │  │ - 基于文件系统           │  │      - 基于向量数据库                    │││
│  │  │ - Markdown + Frontmatter │  │      - 语义相似度搜索                    │││
│  │  └─────────────────────────┘  └─────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘││
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Domain 层设计

### 2.1 记忆实体 (Memory)

**文件**: `backend/domain/models/memory/memory.py`

```python
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class MemoryType(str, Enum):
    """记忆类型 - 对应 free-code 的四种类型"""
    USER = "user"           # 用户信息
    FEEDBACK = "feedback"   # 反馈指导
    PROJECT = "project"     # 项目信息
    REFERENCE = "reference" # 外部引用


class MemoryMetadata(BaseModel):
    """记忆元数据"""
    description: Optional[str] = None
    source: Optional[str] = None  # 来源会话/工具
    confidence: float = 1.0       # 提取置信度
    extracted_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        frozen = True


class Memory(BaseModel):
    """
    记忆实体 - 对应 free-code 的 memory file
    
    文件格式:
    ```markdown
    ---
    type: feedback
    description: 用户偏好简要响应
    ---
    
    用户不喜欢冗余的总结
    ```
    """
    id: str                       # 唯一标识 (uuid)
    type: MemoryType
    content: str                  # 记忆内容 (markdown)
    metadata: MemoryMetadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    project_path: str            # 所属项目路径
    
    # 可选: 向量嵌入 (用于语义搜索)
    embedding: Optional[list[float]] = None
    
    class Config:
        frozen = False
    
    def to_markdown(self) -> str:
        """转换为 Markdown 格式存储"""
        frontmatter = f"""---
type: {self.type.value}
description: {self.metadata.description or ''}
extracted_at: {self.metadata.extracted_at.isoformat()}
---

"""
        return frontmatter + self.content
    
    @classmethod
    def from_markdown(cls, file_path: str, content: str) -> "Memory":
        """从 Markdown 文件解析"""
        # 解析 frontmatter
        import yaml
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2].strip()
        else:
            frontmatter = {}
            body = content
        
        return cls(
            id=Path(file_path).stem,
            type=MemoryType(frontmatter.get('type', 'project')),
            content=body,
            metadata=MemoryMetadata(
                description=frontmatter.get('description'),
                extracted_at=datetime.fromisoformat(
                    frontmatter.get('extracted_at', datetime.now().isoformat())
                )
            ),
            project_path=str(Path(file_path).parent)
        )
```

### 2.2 仓库接口 (MemoryRepository)

**文件**: `backend/domain/repositories/memory_repository.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from ..models.memory import Memory, MemoryType


class MemoryRepository(ABC):
    """
    记忆仓库接口 - Clean Architecture 的端口
    
    实现可以是:
    - FileSystemMemoryRepository: 基于文件系统 (free-code 风格)
    - VectorMemoryRepository: 基于向量数据库 (未来扩展)
    """
    
    @abstractmethod
    async def save(self, memory: Memory) -> None:
        """保存记忆"""
        pass
    
    @abstractmethod
    async def find_by_id(self, memory_id: str, project_path: str) -> Optional[Memory]:
        """通过 ID 查找"""
        pass
    
    @abstractmethod
    async def list_by_type(
        self, 
        project_path: str, 
        memory_type: Optional[MemoryType] = None
    ) -> List[Memory]:
        """按类型列出记忆"""
        pass
    
    @abstractmethod
    async def search(
        self, 
        project_path: str, 
        query: str, 
        limit: int = 5
    ) -> List[Memory]:
        """
        搜索相关记忆
        - 基础实现: 基于关键词匹配
        - 高级实现: 基于向量相似度
        """
        pass
    
    @abstractmethod
    async def delete(self, memory_id: str, project_path: str) -> bool:
        """删除记忆"""
        pass
    
    @abstractmethod
    async def get_entrypoint(self, project_path: str) -> str:
        """获取 MEMORY.md 入口文件内容"""
        pass
```

---

## 3. Application 层设计

### 3.1 记忆服务 (MemoryService)

**文件**: `backend/application/services/memory_service.py`

```python
from typing import List, Optional
from ...domain.models.memory import Memory, MemoryType
from ...domain.repositories.memory_repository import MemoryRepository


class MemoryService:
    """
    记忆服务 - 应用层用例协调器
    
    对应 free-code 的:
    - loadMemoryPrompt() -> get_memories_for_prompt()
    - extractMemories() -> extract_from_conversation()
    """
    
    def __init__(self, repository: MemoryRepository):
        self._repo = repository
    
    async def create_memory(
        self,
        project_path: str,
        memory_type: MemoryType,
        content: str,
        description: Optional[str] = None
    ) -> Memory:
        """创建新记忆"""
        import uuid
        memory = Memory(
            id=str(uuid.uuid4()),
            type=memory_type,
            content=content,
            metadata=MemoryMetadata(
                description=description,
                extracted_at=datetime.now()
            ),
            project_path=project_path
        )
        await self._repo.save(memory)
        return memory
    
    async def get_relevant_memories(
        self, 
        project_path: str, 
        query: str,
        limit: int = 5
    ) -> List[Memory]:
        """
        获取与查询相关的记忆
        
        对应 free-code 的 findRelevantMemories()
        可以扩展为使用 LLM 选择最相关的记忆
        """
        # 基础实现: 返回所有记忆（按时间排序）
        memories = await self._repo.list_by_type(project_path)
        
        # 如果有查询，进行简单过滤
        if query:
            memories = [
                m for m in memories 
                if query.lower() in m.content.lower() 
                or (m.metadata.description and query.lower() in m.metadata.description.lower())
            ]
        
        # 按时间倒序，限制数量
        memories.sort(key=lambda m: m.metadata.extracted_at, reverse=True)
        return memories[:limit]
    
    async def build_memory_prompt(self, project_path: str) -> str:
        """
        构建记忆系统提示词
        
        对应 free-code 的 loadMemoryPrompt()
        """
        entrypoint = await self._repo.get_entrypoint(project_path)
        return f"""<memory>
{entrypoint}
</memory>"""
```

### 3.2 记忆提取器 (MemoryExtractor)

**文件**: `backend/application/services/memory_extractor.py`

```python
from typing import List
from ...domain.models.memory import Memory, MemoryType
from ...infrastructure.llm_provider import LLMProvider


class MemoryExtractor:
    """
    记忆提取器 - 从对话中提取有价值的记忆
    
    对应 free-code 的 extractMemories 服务
    """
    
    def __init__(self, llm_provider: LLMProvider):
        self._llm = llm_provider
    
    async def extract_from_conversation(
        self,
        project_path: str,
        conversation_history: List[dict],
        existing_memories: List[Memory]
    ) -> List[Memory]:
        """
        从对话历史中提取新记忆
        
        提示词设计参考 free-code 的 extractMemories/prompts.ts
        """
        system_prompt = """You are extracting durable memories from a conversation.

Extract memories that capture:
1. USER: User's role, goals, responsibilities, knowledge
2. FEEDBACK: Guidance about what to avoid or keep doing
3. PROJECT: Ongoing work, deadlines, bugs, incidents
4. REFERENCE: Pointers to external systems

Rules:
- Only capture context NOT derivable from code/git
- Convert relative dates to absolute dates
- Include WHY for project/feedback memories
- Be selective - quality over quantity

Return a JSON array of memories:
[{
  "type": "user|feedback|project|reference",
  "description": "one-line summary",
  "content": "full memory content"
}]"""

        # 构建上下文
        context = self._format_conversation(conversation_history)
        
        # 调用 LLM 提取
        response = await self._llm.complete(
            system=system_prompt,
            messages=[{"role": "user", "content": context}]
        )
        
        # 解析结果
        return self._parse_extraction_response(project_path, response)
    
    def _format_conversation(self, history: List[dict]) -> str:
        """格式化对话历史"""
        lines = []
        for msg in history:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            lines.append(f"{role.upper()}: {content[:500]}")  # 截断
        return "\n\n".join(lines)
```

---

## 4. Infrastructure 层设计

### 4.1 Mixin 模式集成

**文件**: `backend/infrastructure/runtime/deep/mixins/memory_mixin.py`

```python
"""MemoryMixin - 记忆功能 Mixin

基于 free-code 的 memdir.ts 和 extractMemories.ts 设计
添加到 DeepAgentRuntime 提供记忆功能
"""

from typing import Any, List, Optional
from pathlib import Path
from loguru import logger

from ..services.memory_service import MemoryService
from ..services.memory_extractor import MemoryExtractor
from ...domain.models.memory import Memory


class MemoryMixin:
    """记忆功能 Mixin"""
    
    # 依赖注入的属性
    _memory_service: Optional[MemoryService] = None
    _memory_extractor: Optional[MemoryExtractor] = None
    _project_path: str = "."
    
    async def _init_memory_system(self) -> None:
        """初始化记忆系统 - 对应 ensureMemoryDirExists"""
        from ...infrastructure.persistence.memory.filesystem_repo import (
            FileSystemMemoryRepository
        )
        
        # 创建仓库
        repo = FileSystemMemoryRepository(self._project_path)
        self._memory_service = MemoryService(repo)
        
        # 确保目录存在
        memory_dir = Path(self._project_path) / ".claude" / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[MemoryMixin] Initialized for {self._project_path}")
    
    async def get_memory_prompt(self) -> str:
        """获取记忆系统提示词 - 注入到 LLM"""
        if not self._memory_service:
            return ""
        return await self._memory_service.build_memory_prompt(self._project_path)
    
    async def save_memory(
        self, 
        memory_type: str, 
        content: str, 
        description: Optional[str] = None
    ) -> Memory:
        """保存记忆"""
        from ...domain.models.memory import MemoryType
        
        if not self._memory_service:
            raise RuntimeError("Memory system not initialized")
        
        memory = await self._memory_service.create_memory(
            project_path=self._project_path,
            memory_type=MemoryType(memory_type),
            content=content,
            description=description
        )
        
        logger.info(f"[MemoryMixin] Saved memory: {memory.id}")
        return memory
    
    async def extract_memories(self, conversation_history: List[dict]) -> List[Memory]:
        """
        从对话历史中提取记忆
        
        对应 free-code 的 extractMemories 功能
        可在查询结束时自动调用
        """
        if not self._memory_extractor or not self._memory_service:
            return []
        
        # 获取现有记忆（避免重复）
        existing = await self._memory_service.get_relevant_memories(
            self._project_path, ""
        )
        
        # 提取新记忆
        new_memories = await self._memory_extractor.extract_from_conversation(
            self._project_path,
            conversation_history,
            existing
        )
        
        # 保存新记忆
        for memory in new_memories:
            await self._memory_service.create_memory(
                project_path=self._project_path,
                memory_type=memory.type,
                content=memory.content,
                description=memory.metadata.description
            )
        
        logger.info(f"[MemoryMixin] Extracted {len(new_memories)} memories")
        return new_memories
    
    async def get_relevant_memories(
        self, 
        query: str, 
        limit: int = 5
    ) -> List[Memory]:
        """获取相关记忆 - 对应 findRelevantMemories"""
        if not self._memory_service:
            return []
        
        return await self._memory_service.get_relevant_memories(
            self._project_path, query, limit
        )
```

### 4.2 文件系统仓库实现

**文件**: `backend/infrastructure/persistence/memory/filesystem_repo.py`

```python
"""
FileSystemMemoryRepository - free-code 风格的文件系统存储

存储结构:
.claude/memory/
├── MEMORY.md           # 入口索引
├── user/              # 用户记忆
├── feedback/          # 反馈记忆
├── project/           # 项目记忆
└── reference/         # 引用记忆
"""

import yaml
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ....domain.models.memory import Memory, MemoryType
from ....domain.repositories.memory_repository import MemoryRepository


class FileSystemMemoryRepository(MemoryRepository):
    """基于文件系统的记忆仓库 - free-code 风格"""
    
    def __init__(self, project_path: str):
        self._base_path = Path(project_path) / ".claude" / "memory"
        self._base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_type_dir(self, memory_type: MemoryType) -> Path:
        """获取类型目录"""
        return self._base_path / memory_type.value
    
    def _get_file_path(self, memory_id: str, memory_type: MemoryType) -> Path:
        """获取记忆文件路径"""
        return self._get_type_dir(memory_type) / f"{memory_id}.md"
    
    async def save(self, memory: Memory) -> None:
        """保存记忆到文件"""
        # 确保类型目录存在
        type_dir = self._get_type_dir(memory.type)
        type_dir.mkdir(exist_ok=True)
        
        # 写入文件
        file_path = self._get_file_path(memory.id, memory.type)
        file_path.write_text(memory.to_markdown(), encoding="utf-8")
        
        # 更新入口文件
        await self._update_entrypoint()
    
    async def find_by_id(
        self, 
        memory_id: str, 
        project_path: str
    ) -> Optional[Memory]:
        """通过 ID 查找"""
        # 在所有类型目录中查找
        for memory_type in MemoryType:
            file_path = self._get_file_path(memory_id, memory_type)
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                return Memory.from_markdown(str(file_path), content)
        return None
    
    async def list_by_type(
        self,
        project_path: str,
        memory_type: Optional[MemoryType] = None
    ) -> List[Memory]:
        """列出记忆"""
        memories = []
        
        types_to_scan = [memory_type] if memory_type else list(MemoryType)
        
        for mt in types_to_scan:
            type_dir = self._get_type_dir(mt)
            if not type_dir.exists():
                continue
            
            for file_path in type_dir.glob("*.md"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    memory = Memory.from_markdown(str(file_path), content)
                    memories.append(memory)
                except Exception:
                    continue  # 跳过损坏的文件
        
        # 按时间排序
        memories.sort(
            key=lambda m: m.metadata.extracted_at, 
            reverse=True
        )
        return memories
    
    async def search(
        self,
        project_path: str,
        query: str,
        limit: int = 5
    ) -> List[Memory]:
        """搜索记忆 - 简单关键词匹配"""
        all_memories = await self.list_by_type(project_path)
        
        # 简单关键词匹配（未来可替换为向量搜索）
        query_lower = query.lower()
        matches = [
            m for m in all_memories
            if query_lower in m.content.lower()
            or (m.metadata.description and query_lower in m.metadata.description.lower())
        ]
        
        return matches[:limit]
    
    async def delete(self, memory_id: str, project_path: str) -> bool:
        """删除记忆"""
        memory = await self.find_by_id(memory_id, project_path)
        if not memory:
            return False
        
        file_path = self._get_file_path(memory_id, memory.type)
        if file_path.exists():
            file_path.unlink()
            await self._update_entrypoint()
            return True
        return False
    
    async def get_entrypoint(self, project_path: str) -> str:
        """生成 MEMORY.md 入口文件"""
        memories = await self.list_by_type(project_path)
        
        # 按类型分组
        by_type: dict[MemoryType, List[Memory]] = {}
        for m in memories:
            by_type.setdefault(m.type, []).append(m)
        
        # 生成索引
        lines = ["# Memory", ""]
        
        for memory_type in MemoryType:
            type_memories = by_type.get(memory_type, [])
            if not type_memories:
                continue
            
            lines.extend([
                f"## {memory_type.value.upper()}",
                ""
            ])
            
            for m in type_memories:
                desc = m.metadata.description or m.content[:50] + "..."
                lines.append(f"- [{m.id}]({m.type.value}/{m.id}.md): {desc}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    async def _update_entrypoint(self) -> None:
        """更新 MEMORY.md 入口文件"""
        entrypoint_content = await self.get_entrypoint(str(self._base_path.parent))
        entrypoint_path = self._base_path / "MEMORY.md"
        entrypoint_path.write_text(entrypoint_content, encoding="utf-8")
```

---

## 5. Runtime 集成

### 5.1 添加到 DeepAgentRuntime

**修改**: `backend/infrastructure/runtime/deep/__init__.py`

```python
from .mixins.memory_mixin import MemoryMixin

class DeepAgentRuntime(
    # ... 其他 Mixin
    MemoryMixin,  # 添加记忆 Mixin
    AbstractAgentRuntime[DeepAgentConfig],
):
    """
    Deep Agent Runtime - 现在包含记忆功能
    """
    
    async def _do_initialize(self) -> None:
        # ... 其他初始化
        
        # 初始化记忆系统
        await self._init_memory_system()
    
    async def send_message(self, ...):
        # 查询前：加载记忆到系统提示词
        memory_prompt = await self.get_memory_prompt()
        
        # ... 发送消息逻辑
        
        # 查询后：提取新记忆
        await self.extract_memories(conversation_history)
```

### 5.2 事件集成

**文件**: `backend/infrastructure/event_bus/memory_events.py`

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MemoryCreatedEvent(BaseModel):
    """记忆创建事件"""
    memory_id: str
    memory_type: str
    project_path: str
    created_at: datetime = datetime.now()


class MemoryExtractedEvent(BaseModel):
    """记忆提取完成事件"""
    count: int
    project_path: str
    extracted_at: datetime = datetime.now()


class MemoryRetrievedEvent(BaseModel):
    """记忆检索事件"""
    query: str
    results_count: int
    project_path: str
```

---

## 6. 接口层集成

### 6.1 HTTP 命令

**文件**: `backend/interfaces/http/commands/memory_commands.py`

```python
from fastapi import APIRouter, Depends
from typing import List, Optional

from ....application.services.memory_service import MemoryService
from ....domain.models.memory import MemoryType

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/")
async def create_memory(
    type: MemoryType,
    content: str,
    description: Optional[str] = None,
    service: MemoryService = Depends(get_memory_service)
):
    """创建记忆"""
    memory = await service.create_memory(
        project_path=".",
        memory_type=type,
        content=content,
        description=description
    )
    return {"id": memory.id, "status": "saved"}


@router.get("/")
async def list_memories(
    type: Optional[MemoryType] = None,
    service: MemoryService = Depends(get_memory_service)
):
    """列出记忆"""
    memories = await service.list_by_type(".", type)
    return memories


@router.post("/search")
async def search_memories(
    query: str,
    limit: int = 5,
    service: MemoryService = Depends(get_memory_service)
):
    """搜索相关记忆"""
    results = await service.get_relevant_memories(".", query, limit)
    return results
```

---

## 7. 与 free-code 的对应关系

| free-code 组件 | 本设计对应 | 说明 |
|----------------|-----------|------|
| `src/memdir/memoryTypes.ts` | `domain/models/memory/memory.py` | MemoryType 枚举 |
| `src/memdir/memdir.ts` | `mixins/memory_mixin.py` | 主逻辑 Mixin |
| `src/memdir/paths.ts` | `filesystem_repo.py` | 路径管理 |
| `src/memdir/memoryScan.ts` | `filesystem_repo.list_by_type()` | 文件扫描 |
| `src/memdir/findRelevantMemories.ts` | `MemoryService.get_relevant_memories()` | 相关记忆检索 |
| `src/memdir/memoryAge.ts` | `Memory.metadata.extracted_at` | 老化管理 |
| `src/services/extractMemories/` | `MemoryExtractor` | 自动提取服务 |
| `src/services/SessionMemory/` | (可选) SessionMemoryMixin | 会话记忆 |
| `src/commands/memory/` | `memory_commands.py` | HTTP 命令 |

---

## 8. 扩展建议

### 8.1 短期（已设计）
- ✅ 基于文件系统的存储
- ✅ Mixin 模式集成
- ✅ 四种记忆类型
- ✅ 自动提取机制

### 8.2 中期
- [ ] **向量嵌入**: 添加 OpenAI/Anthropic embedding 支持
- [ ] **语义搜索**: 基于相似度的记忆检索
- [ ] **老化策略**: 自动归档旧记忆
- [ ] **团队记忆**: 共享记忆空间

### 8.3 长期
- [ ] **记忆压缩**: 类似 free-code 的 compact 功能
- [ ] **跨项目记忆**: 用户级全局记忆
- [ ] **记忆可视化**: Web UI 浏览和管理

---

## 9. 总结

本设计将 free-code 的记忆系统架构嵌入到当前项目中，遵循：

1. **Clean Architecture**: 分层清晰，依赖向内
2. **Mixin 模式**: 通过 MemoryMixin 添加到 Runtime
3. **Pydantic 优先**: 所有模型使用 Pydantic
4. **事件驱动**: 通过 EventBus 解耦
5. **free-code 风格**: Markdown + Frontmatter 存储

实施步骤:
1. 实现 Domain 层模型和接口
2. 实现 Infrastructure 层仓库和 Mixin
3. 添加到 DeepAgentRuntime
4. 添加 HTTP 命令接口
5. 测试和调优
