# CLAUDE.md

项目核心规则与约束。

## 1. 软件设计原则

- **Clean Architecture**: Interfaces → Application → Domain → Infrastructure 分层
- **Pydantic 优先**: 所有数据模型使用 Pydantic，禁止裸字典传递业务数据
- **事件驱动**: 模块间通信通过 EventBus，禁止直接调用
- **单一职责**: 函数 max 50 行，类 max 200 行，文件 max 300 行

## 2. 虚拟环境

```bash
# 必须使用 .venv-new（Windows）
.venv-new/Scripts/activate

# 安装依赖
pip install -r requirements.txt
```

## 3. 代码提交规范

**必须解决所有 pre-commit 钩子问题，禁止绕过。**

```bash
# 提交前自动运行
make check        # 全部检查
make fix          # 自动修复
make check-bare-dicts  # 裸字典检测

# 禁止跳过钩子（除非紧急情况）
git commit -m "xxx" --no-verify  # ❌ 禁止
```

## 4. 技术栈

- **Backend**: Python 3.11+, FastAPI, Pydantic v2
- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS v4
- **Runtime**: SimpleRuntime (基础) / DeepAgentRuntime (高级)

## 5. 目录结构

```
backend/
├── infrastructure/runtime/base/    # 公共基类
├── infrastructure/runtime/simple/  # Simple Runtime
├── infrastructure/runtime/deep/    # Deep Runtime
└── infrastructure/event_bus/       # 事件总线
```
