# 遗留代码清理规范

## 功能要求

### FR1: AgentEngine 删除

- 必须删除 `core/engine.py` 文件
- 必须删除所有对 `AgentEngine` 的直接导入
- 必须确保删除后无导入错误

### FR2: 备份文件清理

- 必须清理 `core/agent/simple/` 目录中的备份文件
- 保留该目录中仍在使用的非备份文件

### FR3: 测试验证

- 运行 `tests/test_agent_runtime.py` 必须全部通过
- 运行 `tests/test_simple_runtime_full.py` 必须全部通过
- 系统启动必须正常

## 文件清单

### 待删除文件
- `core/engine.py` - 已弃用的 AgentEngine 类
- `core/agent/simple/` 中的 `*.bak`, `*.old`, `*_backup.py` 等备份文件

### 需要检查的导入
搜索以下模式：
- `from core.engine import`
- `from core.engine import AgentEngine`
- `import core.engine`

## 验收标准

- [x] `core/engine.py` 不存在
- [x] 核心代码中无 `AgentEngine` 导入（文档除外）
- [x] 单元测试通过（test_agent_runtime.py 36/36 通过）
- [x] 核心模块可正常导入
