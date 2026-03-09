# Finance 技能文件关系与模块化说明

本文档梳理 finance 文件夹内的模块关系，说明职责边界与复用方式，确保 SQL 生成逻辑清晰、模块化。

## 顶层入口

- SKILL.md
  - 技能说明与使用范围。
  - 入口描述应指向 references 与 scripts 中的核心规则/模板。

## references（规则与规范）

- metadata.md
  - 表与字段映射的业务元数据说明。
- react_overview.md
  - ReACT 的整体方法与执行约束摘要。
- react_constraints.md
  - 字段/字典/联表规则与约束。
- react_examples.md
  - SQL 生成示例库（分场景）。
- react_rules.md
  - 规则细化（分摊、对比、异常处理等）。
- workflow.md
  - 与 src/graph/graph.py 一致的工作流说明。
- module_map.md
  - 当前文档：模块关系与职责划分。

## scripts（实现与示例）

### 核心生成器

- allocation_utils.py
  - 单一来源的分摊 SQL 生成器。
  - 包含 ALLOC_TEMPLATE 与 generate_alloc_sql。
- generate_alloc_sql.py
  - 兼容层，直接 re-export allocation_utils 的实现。
  - 便于保持历史脚本引用不变。

### 动态 SQL 示例

- dynamic_skill_sql.py
  - 简化版意图分析 → SQL 构造 → 执行示例。
  - 演示关键词匹配与默认场景过滤。

### 示例脚本

- example_overview.py

示例脚本统一通过 allocation_utils.generate_alloc_sql 构建 SQL，便于集中维护模板逻辑。

### tests

- scripts/tests
  - 脚本级功能测试或本地调试用例。

## 推荐调用路径

1. 用户问题 → select_skill
2. 读取 references 规则与 metadata
3. 使用 allocation_utils.generate_alloc_sql 生成 SQL
4. SQL 校验与执行 → 输出结果

## 模块化原则

- 模板只在 allocation_utils.py 定义，禁止多处复制。
- 示例与测试只能依赖公开函数（generate_alloc_sql）。
- 规则与约束全部放在 references，脚本不重复写规则文字。
