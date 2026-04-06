# Database Query Skill Patterns

Best practices for creating skills that interact with databases.

## Overview

Database query skills require special consideration because:
- Table schemas may change over time
- LLMs need to understand data structure before generating queries
- Query correctness is critical (wrong queries produce wrong answers)
- Different databases have different SQL dialects

## Standard Workflow for Database Skills

### 1. Schema Discovery First

Always provide a standard schema discovery query sequence in SKILL.md:

```markdown
## 步骤 1: 了解数据结构

首次使用或不确定表结构时，必须执行以下查询：

```sql
-- 1. 查询主表结构
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'YOUR_TABLE_NAME'
ORDER BY ordinal_position;

-- 2. 查询示例数据（前3行）
SELECT * FROM YOUR_TABLE_NAME LIMIT 3;

-- 3. 查询关键字段的枚举值
SELECT DISTINCT status FROM YOUR_TABLE_NAME;
```
```

### 2. Document Table Relationships

Create a `references/schema.md` file documenting:
- Table names and purposes
- Column definitions and data types
- Relationships between tables
- Common query patterns

### 3. Provide SQL Templates

Create a `references/sql_templates.md` with:
- Standard SELECT patterns
- JOIN patterns
- Aggregation examples
- Filter patterns

### 4. Query Building Guidelines

Include in SKILL.md:
- How to determine which tables to query
- How to handle table aliases
- Required WHERE clauses
- Common pitfalls

## Example: Finance Skill Structure

```
finance/
├── SKILL.md                      # Main skill file with workflow
├── references/
│   ├── schema_query.md          # Schema discovery queries
│   ├── react_constraints.md     # Domain-specific constraints
│   ├── react_examples.md        # Query examples
│   └── sql_templates.md         # Reusable SQL templates
└── scripts/
    └── allocation_utils.py      # SQL generation utilities
```

## SKILL.md Template for Database Skills

```markdown
---
name: your-database-skill
description: Query and analyze data from X database. Use when user asks about Y, Z, or any data analysis questions involving [tables/domains].
---

# Your Database Skill

## Standard Workflow

### Step 1: Schema Discovery

If table structure is unknown, run:

```sql
-- List all tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Get table structure
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'TABLE_NAME'
ORDER BY ordinal_position;

-- Get sample data
SELECT * FROM TABLE_NAME LIMIT 3;
```

### Step 2: Determine Query Type

| User Question Pattern | Query Type | Reference File |
|----------------------|------------|----------------|
| "how many", "count" | Aggregation | references/aggregations.md |
| "list", "show me" | List/Select | references/select_patterns.md |
| "compare", "vs" | Comparison | references/comparisons.md |

### Step 3: Build and Execute Query

1. Read the appropriate reference file
2. Use provided SQL templates
3. Fill in parameters based on user intent
4. Execute using `run_sql_query`

### Step 4: Interpret Results

- Explain what the data means
- Highlight any anomalies
- Provide context for numbers

## Key Rules

- Rule 1: Always validate table names before querying
- Rule 2: Use parameterized queries when possible
- Rule 3: Check for NULL values in aggregations
- Rule 4: Document any assumptions made

## Reference Files

| File | Purpose |
|------|---------|
| references/schema.md | Table schemas and relationships |
| references/sql_templates.md | Reusable SQL patterns |
| references/examples.md | Common query examples |
```

## Anti-Patterns to Avoid

### Don't: Hardcode Schema Information

❌ **Bad**: Embedding column lists in SKILL.md
```markdown
The users table has: id, name, email, created_at...
```

✅ **Good**: Providing a query to discover schema
```markdown
Run: SELECT column_name FROM information_schema.columns WHERE table_name = 'users';
```

### Don't: Assume SQL Dialect

❌ **Bad**: Using dialect-specific syntax without documentation
```sql
SELECT TOP 10 * FROM table  -- SQL Server only
```

✅ **Good**: Documenting dialect or using standard SQL
```sql
SELECT * FROM table LIMIT 10  -- Standard SQL
```

### Don't: Skip Error Handling

❌ **Bad**: No guidance on what to do when queries fail

✅ **Good**: Include troubleshooting steps
```markdown
If query fails:
1. Check table name exists: SELECT table_name FROM information_schema.tables
2. Verify column names: SELECT column_name FROM information_schema.columns WHERE table_name = 'X'
3. Check for syntax errors in your SQL
```

## Testing Database Skills

Before packaging, test:

1. **Schema discovery queries** work correctly
2. **Example queries** return expected results
3. **Edge cases** are handled (empty results, NULL values)
4. **Error messages** are helpful when queries fail

## Progressive Disclosure for Database Skills

1. **SKILL.md** contains the workflow and essential rules
2. **references/schema.md** contains detailed schema info
3. **references/sql_templates.md** contains reusable queries
4. **references/examples.md** contains domain-specific examples

Keep SKILL.md under 200 lines. Move detailed information to reference files.
