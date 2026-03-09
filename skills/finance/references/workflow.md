# 工作流说明（finance skill）

本文档描述 src/graph/graph.py 中的核心工作流，并明确如何在流程中保证 SQL 生成准确性与可执行性。

## 目标

- 以清晰、稳定的节点顺序完成从用户问题到最终回答的闭环。
- 在 SQL 生成与执行阶段加入严格的校验与失败回退，确保最终 SQL 可在目标数据库执行。
- 保证技能上下文、表结构与业务约束被准确传递给 SQL 生成节点。

## 主流程（当前实现）

1. 选择技能（select_skill）
   - 根据用户问题和技能摘要选择目标技能。
   - 加载完整技能内容（含 references/scripts），为后续 SQL 生成提供业务规则与表名线索。
   - 提取 table_names（如从 skill 内容中解析出核心表）。

2. 加载上下文（load_context）
   - 根据 table_names 拉取数据源结构信息。
   - 生成 data_source_schema，作为 SQL 生成的结构依据。

3. 生成 SQL（generate_sql）
   - 结合 user_query、skill_context、data_source_schema 生成 SQL。
   - 严格遵守 finance 规则（见 references/react_rules.md）。

4. SQL 校验（sql_validation）
   - 校验 SQL 安全性与合规性。
   - 未通过时回退到 generate_sql 重新生成。

5. SQL 执行（sql_execution）
   - 执行 SQL 并返回结果。
   - 若执行出错，回退到 generate_sql 重新生成。

6. 精炼答案（refine_answer）
   - 结合查询结果生成最终回答。

## 关键路由规则

- sql_validation：
  - sql_valid == true -> sql_execution
  - 否则 -> generate_sql

- sql_execution：
  - 执行出错 -> generate_sql
  - 否则 -> refine_answer

> 说明：当前流程入口是 select_skill，未启用意图分析与结果审查节点。

## 确保 SQL 准确性的关键要求

1. 表名必须明确
   - table_names 必须从 skill 内容中可靠提取。
   - 为空时无法加载 schema，SQL 生成会缺失结构依据。

2. 技能规则优先
   - finance 规则必须优先于通用策略，尤其是分摊计算、预算/实际对比逻辑。
   - 参考 references/react_rules.md 与 references/react_constraints.md。

3. 数据源结构一致
   - data_source_schema 必须来自 load_context 的真实结构。
   - SQL 生成必须使用 schema 中存在的字段名与表名。

4. 单语句、可执行
   - SQL 必须为单条语句（允许 CTE）。
   - 禁止多语句、临时表与非 SQL Server 语法。

5. 错误回退策略
   - 校验失败或执行失败必须返回 generate_sql 重新生成。
   - 直到 sql_validation 通过并执行成功才进入 refine_answer。

## 建议的补充约束（可选）

- 当 table_names 为空时，建议直接回退到 select_skill 或触发提示，让模型补充表名。
- 可恢复结果审查节点（review_result）用于过滤无效结果，减少误答。

## 相关参考

- references/react_rules.md
- references/react_constraints.md
- references/react_examples.md
