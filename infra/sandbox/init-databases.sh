#!/bin/bash
set -e

# 创建 agent_memory 数据库（如果不存在）
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE agent_memory'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'agent_memory')\gexec
EOSQL

# 在 agent_memory 中创建表
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "agent_memory" <<-EOSQL
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

    CREATE INDEX IF NOT EXISTS idx_memories_user_created ON memories(user_id, created_at);
    CREATE INDEX IF NOT EXISTS idx_memories_user_project ON memories(user_id, project_path);
    CREATE INDEX IF NOT EXISTS idx_memories_user_type ON memories(user_id, type);
    CREATE INDEX IF NOT EXISTS idx_memories_search ON memories(user_id, name, description, content);

    COMMENT ON TABLE memories IS 'Agent 记忆存储';
EOSQL

echo "Database initialization completed!"
