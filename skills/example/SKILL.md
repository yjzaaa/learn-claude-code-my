---
name: example
description: An example skill demonstrating best practices for Skill Engine compatibility. Use when users ask about example workflows, templates, or patterns. Keywords: example, template, pattern, workflow, best-practice
---

# Example Skill

This is an example skill that demonstrates best practices for Skill Engine compatibility.

## When to Use This Skill

Use this skill when:
- User asks for examples or templates
- User needs guidance on patterns
- User wants to understand workflows

## Available Tools

This skill assumes the following tools are available:
- `read_file` / `write_file`: File operations
- `list_dir`: Directory listing
- `shell` commands: System operations

## Workflow

### Step 1: Understand Requirements

Ask clarifying questions if needed:
- What is the goal?
- What are the constraints?
- What is the expected output?

### Step 2: Plan Approach

1. Break down the task into steps
2. Identify required tools
3. Consider edge cases

### Step 3: Execute

Follow the plan step by step:
```python
# Example code pattern
result = execute_step_1()
if result.success:
    execute_step_2()
```

### Step 4: Validate

- Check output correctness
- Verify all requirements met
- Handle any errors gracefully

## File References

Reference files relative to the skill directory:
- Templates: `{baseDir}/templates/`
- Scripts: `{baseDir}/scripts/`
- Data: `{baseDir}/data/`

## Common Patterns

### Pattern 1: Error Handling

Always include error handling:
```python
try:
    result = risky_operation()
except SpecificError as e:
    handle_error(e)
```

### Pattern 2: Resource Cleanup

Clean up resources after use:
```python
resource = acquire_resource()
try:
    use_resource(resource)
finally:
    release_resource(resource)
```

## Output Format

Provide results in this format:

```markdown
## Summary
Brief description of what was done.

## Details
- Point 1
- Point 2

## Next Steps
Suggestions for follow-up actions.
```

## Notes

- This skill uses `{baseDir}` placeholder for paths
- The placeholder will be replaced with the actual skill directory path
- Always verify file existence before reading
