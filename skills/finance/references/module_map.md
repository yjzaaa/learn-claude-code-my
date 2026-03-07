# Finance 技能文件关系与模块化说明

本文档梳理 finance 文件夹内的模块关系，说明职责边界与复用方式。

## 顶层入口

- **SKILL.md**
  - 技能说明与使用范围
  - 包含 SQL 生成流程、查询模板、业务规则
  - 指向 references 中的核心规则文档

## references（规则与规范）

- **metadata.md**
  - 表与字段映射的业务元数据说明

- **react_overview.md**
  - ReACT 的整体方法与执行约束摘要

- **react_constraints.md**
  - 字段/字典/联表规则与约束

- **react_examples.md**
  - SQL 生成示例库（分场景）

- **react_rules.md**
  - 规则细化（分摊、对比、异常处理等）

- **workflow.md**
  - 工作流说明

- **module_map.md**
  - 当前文档：模块关系与职责划分

## scripts（实现）

- **sql_query.py**
  - 核心 SQL 执行引擎
  - 提供 `run_sql_query(sql: str) -> str` 函数
  - 返回 JSON 格式结果

- **__init__.py**
  - 模块导出文件

## SQL 生成流程

1. **用户问题** → 意图识别
2. **查询表结构** → 确认字段名和数据类型
3. **选择模板** → 根据需求类型选择对应 SQL 模板
4. **生成 SQL** → 使用确认的字段名填充模板
5. **执行 SQL** → 通过 `run_sql_query()` 执行
6. **分析结果** → Python 中完成汇总/对比/趋势分析
7. **输出结论** → 自然语言回答

## 模块化原则

- 规则与约束全部放在 references，scripts 只负责执行
- SQL 模板在 SKILL.md 中统一定义
- 所有脚本通过 `run_sql_query()` 执行 SQL，不直接操作数据库
