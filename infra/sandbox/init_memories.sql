-- 记忆系统数据库初始化

CREATE DATABASE IF NOT EXISTS agent_memory;

\c agent_memory;

-- 记忆表
CREATE TABLE IF NOT EXISTS memories (
    id VARCHAR(32) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    project_path VARCHAR(512) DEFAULT '',
    type VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_memories_user_created ON memories(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_memories_user_project ON memories(user_id, project_path);
CREATE INDEX IF NOT EXISTS idx_memories_user_type ON memories(user_id, type);
CREATE INDEX IF NOT EXISTS idx_memories_search ON memories(user_id, name, description, content);

-- 注释
COMMENT ON TABLE memories IS 'Agent 记忆存储';
COMMENT ON COLUMN memories.type IS '记忆类型: user, feedback, project, reference';
COMMENT ON COLUMN memories.user_id IS '用户ID，用于数据隔离';
