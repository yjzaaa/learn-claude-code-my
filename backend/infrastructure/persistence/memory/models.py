"""
Memory SQLAlchemy Models - 记忆数据库模型

使用 SQLAlchemy 定义 Memory 的数据库表结构。
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MemoryModel(Base):
    """记忆数据库模型

    表名: memories
    主键: id
    索引: user_id + created_at (用于按用户查询)
          user_id + project_path (用于按项目查询)
          user_id + type (用于按类型查询)
    """

    __tablename__ = "memories"

    id = Column(String(32), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    project_path = Column(String(512), nullable=False, default="")
    type = Column(String(20), nullable=False)  # user/feedback/project/reference
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    # 复合索引
    __table_args__ = (
        Index("idx_memories_user_created", "user_id", "created_at"),
        Index("idx_memories_user_project", "user_id", "project_path"),
        Index("idx_memories_user_type", "user_id", "type"),
        Index("idx_memories_search", "user_id", "name", "description", "content"),
    )

    def to_entity(self):
        """转换为领域实体"""
        from backend.domain.models.memory.memory import Memory
        from backend.domain.models.memory.types import MemoryType

        return Memory(
            id=self.id,
            user_id=self.user_id,
            project_path=self.project_path,
            type=MemoryType(self.type),
            name=self.name,
            description=self.description,
            content=self.content,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, memory) -> "MemoryModel":
        """从领域实体创建"""
        return cls(
            id=memory.id,
            user_id=memory.user_id,
            project_path=memory.project_path,
            type=memory.type.value,
            name=memory.name,
            description=memory.description,
            content=memory.content,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
        )
