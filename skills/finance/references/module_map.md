# Finance 技能文件关系与模块化说明

## 顶层入口

- `SKILL.md`
  - 定义技能目标、工作流程、文档分工和唯一执行脚本。

## references（只放规则与模板，不放可执行代码）

- `metadata.md`
  - 业务表清单和意图映射。
- `schema_query_guide.md`
  - 字段结构探测 SQL 指南。
- `sql_templates.md`
  - 常用 SQL 模板与参数说明。
- `react_rules.md`
  - 业务硬规则。
- `react_constraints.md`
  - 字段约束与术语约束。
- `react_examples.md`
  - 问题类型与模板索引。
- `react_overview.md`
  - 执行范式总览。
- `workflow.md`
  - 标准执行步骤与回退策略。
- `module_map.md`
  - 当前文档。

## scripts（只保留一个执行脚本）

- `sql_query.py`
  - 唯一 SQL 执行入口。
  - 内置 SQL 合法性私有校验。
  - 校验失败时输出结构化错误，供模型重写 SQL。

## 推荐调用路径

1. 读取 `metadata.md` 和规则文档。
2. 必要时按 `schema_query_guide.md` 查询字段结构。
3. 按 `sql_templates.md` 组装 SQL。
4. 使用 `scripts/sql_query.py` 执行。
5. 根据结果生成自然语言结论。
