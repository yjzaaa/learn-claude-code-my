# 登录系统设计文档

## 概述

基于 OpenAPI 规范设计的 JWT 认证系统，支持：
- 标准登录（用户名/密码）
- 自动登录（开发模式，admin免密登录）
- Token 刷新和会话管理
- 多设备登录支持

## 目录结构

```
backend/
├── application/
│   ├── dto/
│   │   ├── requests.py          # 现有请求DTO
│   │   ├── responses.py         # 现有响应DTO
│   │   └── auth_dto.py          # [新增] 认证相关DTO
│   └── services/
│       ├── auth_service.py      # [新增] 认证服务
│       └── ...                  # 其他服务
├── infrastructure/
│   ├── persistence/
│   │   └── auth/
│   │       ├── __init__.py
│   │       ├── database.py      # 数据库连接
│   │       ├── models.py        # SQLAlchemy模型
│   │       └── repository.py    # 数据访问层
│   └── config.py                # 配置（已含JWTConfig）
├── interfaces/
│   └── http/
│       ├── dependencies/
│       │   ├── __init__.py
│       │   └── auth.py          # [新增] 认证依赖项
│       ├── routes/
│       │   ├── auth.py          # [新增] 认证路由
│       │   └── ...              # 其他路由
│       └── app.py               # 应用入口
└── domain/
    └── ...                      # 领域模型

docs/openspec/
├── auth-spec.yaml               # [新增] OpenAPI规范
└── AUTH_DESIGN.md               # [新增] 本设计文档
```

## 数据库设计

### 表结构

```sql
-- 用户表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(32) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    display_name VARCHAR(64),
    role VARCHAR(16) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- 用户会话表
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    client_id VARCHAR(64) UNIQUE NOT NULL,
    refresh_token_hash VARCHAR(256),
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    
    CONSTRAINT fk_user_sessions_user 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX ix_user_sessions_user_active ON user_sessions(user_id, is_active);
CREATE INDEX ix_user_sessions_expires ON user_sessions(expires_at);

-- 刷新令牌表
CREATE TABLE refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token_hash VARCHAR(256) UNIQUE NOT NULL,
    session_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    revoked_by VARCHAR(32),
    
    CONSTRAINT fk_refresh_tokens_user 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_refresh_tokens_session 
        FOREIGN KEY (session_id) REFERENCES user_sessions(id) ON DELETE CASCADE
);

CREATE INDEX ix_refresh_tokens_user_revoked ON refresh_tokens(user_id, revoked_at);
CREATE INDEX ix_refresh_tokens_session ON refresh_tokens(session_id, revoked_at);
```

## API 端点

### 1. 自动登录（开发模式）

```http
POST /api/auth/auto-login
Content-Type: application/json

{
    "client_id": "optional-client-id"
}
```

**响应:**
```json
{
    "success": true,
    "data": {
        "user": {
            "id": 1,
            "username": "admin",
            "display_name": "管理员",
            "role": "admin",
            "created_at": "2024-01-01T00:00:00Z",
            "last_login": "2024-01-15T10:30:00Z"
        },
        "tokens": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2ggdG9rZW4...",
            "token_type": "bearer",
            "expires_in": 86400
        },
        "client_id": "1-abc123"
    }
}
```

### 2. 标准登录

```http
POST /api/auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "admin123"
}
```

### 3. 注册

```http
POST /api/auth/register
Content-Type: application/json

{
    "username": "newuser",
    "password": "password123",
    "display_name": "新用户"
}
```

### 4. 获取当前用户

```http
GET /api/auth/me
Authorization: Bearer {access_token}
```

### 5. 刷新 Token

```http
POST /api/auth/refresh
Content-Type: application/json

{
    "refresh_token": "{refresh_token}"
}
```

### 6. 登出

```http
POST /api/auth/logout
X-Client-ID: {client_id}
Authorization: Bearer {access_token}
```

## JWT Token 结构

### Access Token Payload

```json
{
    "sub": "1",
    "username": "admin",
    "role": "admin",
    "type": "access",
    "exp": 1705312800,
    "iat": 1705226400,
    "jti": "unique-token-id"
}
```

### Token 配置

```python
# config.yaml
jwt:
    secret_key: "your-secret-key"  # 生产环境使用强密钥
    algorithm: "HS256"
    expire_minutes: 1440  # 24小时
```

## 认证流程

### 自动登录流程

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /api/auth/auto-login
       │
       ▼
┌─────────────┐     ┌─────────────────┐
│  Auth Route  │────▶│  AuthService    │
└──────┬──────┘     └─────────────────┘
       │                │
       │                │ 1. 检查/创建admin用户
       │                │ 2. 创建会话
       │                │ 3. 生成JWT
       │                ▼
       │            ┌─────────────────┐
       │            │  返回Token + 用户 │
       │            └─────────────────┘
       │
       ▼
┌─────────────┐
│  返回响应    │
│  tokens +   │
│  user info  │
└─────────────┘
```

### 标准认证流程

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /api/auth/login
       │ {username, password}
       │
       ▼
┌─────────────┐     ┌─────────────────┐
│  Auth Route  │────▶│  AuthService    │
└──────┬──────┘     └─────────────────┘
       │                │
       │                │ 1. 验证密码
       │                │ 2. 创建会话
       │                │ 3. 生成JWT
       │                ▼
       │            ┌─────────────────┐
       │            │  返回Token + 用户 │
       │            └─────────────────┘
       │
       ▼
┌─────────────┐
│ 后续请求     │
│ Authorization: Bearer {token}
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ get_current_user │
│ 验证JWT并解析   │
└─────────────┘
```

## 安全考虑

1. **密码存储**: 使用 bcrypt 哈希
2. **Token 存储**: 只存储刷新令牌的 SHA256 哈希
3. **HTTPS**: 生产环境必须使用 HTTPS
4. **Token 过期**: Access token 24小时过期，Refresh token 30天过期
5. **会话撤销**: 支持单点登出和全部登出
6. **自动登录限制**: 仅在开发环境启用

## 使用示例

### Python 客户端

```python
import requests

BASE_URL = "http://localhost:8001"

# 自动登录
response = requests.post(f"{BASE_URL}/api/auth/auto-login", json={})
data = response.json()["data"]
access_token = data["tokens"]["access_token"]
client_id = data["client_id"]

# 使用token访问受保护接口
headers = {
    "Authorization": f"Bearer {access_token}",
    "X-Client-ID": client_id
}
response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
print(response.json()["data"])

# 刷新token
refresh_token = data["tokens"]["refresh_token"]
response = requests.post(
    f"{BASE_URL}/api/auth/refresh",
    json={"refresh_token": refresh_token}
)
new_access_token = response.json()["data"]["access_token"]

# 登出
requests.post(
    f"{BASE_URL}/api/auth/logout",
    headers={"X-Client-ID": client_id}
)
```

### cURL

```bash
# 自动登录
curl -X POST http://localhost:8001/api/auth/auto-login \
  -H "Content-Type: application/json" \
  -d '{}'

# 标准登录
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 获取当前用户
curl http://localhost:8001/api/auth/me \
  -H "Authorization: Bearer {token}"
```

## 依赖需求

```
python-jose[cryptography]  # JWT处理
passlib[bcrypt]            # 密码哈希
asyncpg                    # PostgreSQL异步驱动（已存在）
```

## 下一步

1. 运行数据库迁移创建表
2. 配置 `.env` 中的 JWT_SECRET_KEY
3. 前端集成自动登录
4. 添加登录页面（可选，非当前阶段）
