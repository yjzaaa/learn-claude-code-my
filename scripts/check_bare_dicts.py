"""检测代码中的裸字典字面量（缺少结构定义的字典）

使用方法:
    python scripts/check_bare_dicts.py backend/

会报告：
    - 函数返回裸字典（无类型注解或注解为 dict/Any）
    - 字典字面量键名拼写不一致
    - 应该使用 Pydantic 模型的场景（基于动态扫描的 schemas）
"""

import ast
import sys
from pathlib import Path
from typing import Any


# 全局缓存，避免重复扫描
_schemas_cache: dict[frozenset[str], str] | None = None


def extract_model_fields_from_schemas(schemas_path: Path) -> dict[frozenset[str], str]:
    """动态扫描 schemas.py 提取 Pydantic 模型字段"""
    model_fields: dict[frozenset[str], str] = {}

    if not schemas_path.exists():
        return model_fields

    try:
        source = schemas_path.read_text(encoding='utf-8')
        tree = ast.parse(source)
    except Exception:
        return model_fields

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # 检查是否是 Pydantic 模型（继承 BaseModel）
            is_pydantic = False
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == 'BaseModel':
                    is_pydantic = True
                    break
                elif isinstance(base, ast.Subscript):
                    if isinstance(base.value, ast.Name) and base.value.id == 'BaseModel':
                        is_pydantic = True
                        break

            if not is_pydantic:
                continue

            # 提取字段名（Field 定义或类型注解）
            fields: set[str] = set()
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.add(item.target.id)
                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            fields.add(target.id)

            if fields:
                model_fields[frozenset(fields)] = node.name

    return model_fields


def get_model_suggestions(project_root: Path) -> dict[frozenset[str], str]:
    """获取模型建议映射（带缓存）"""
    global _schemas_cache
    if _schemas_cache is not None:
        return _schemas_cache

    # 扫描多个可能的 schemas 位置
    schema_paths = [
        project_root / "backend" / "domain" / "models" / "schemas.py",
        project_root / "backend" / "schemas" / "models.py",
        project_root / "backend" / "schemas.py",
    ]

    for path in schema_paths:
        if path.exists():
            _schemas_cache = extract_model_fields_from_schemas(path)
            if _schemas_cache:
                return _schemas_cache

    _schemas_cache = {}
    return _schemas_cache


def find_matching_model(keys: set[str], project_root: Path) -> str | None:
    """根据键名动态查找匹配的 Pydantic 模型"""
    model_suggestions = get_model_suggestions(project_root)

    if not model_suggestions:
        return None

    # 精确匹配
    for pattern, model in model_suggestions.items():
        if pattern == keys:
            return model

    # 部分匹配（70% 以上键名匹配）
    best_match = None
    best_score = 0
    for pattern, model in model_suggestions.items():
        if not pattern:
            continue
        intersection = pattern & keys
        match_ratio = len(intersection) / len(pattern)
        if match_ratio >= 0.7:  # 70% 匹配度
            score = len(intersection)
            if score > best_score:
                best_score = score
                best_match = model

    return best_match


class BareDictChecker(ast.NodeVisitor):
    """AST 访问者，检测裸字典使用"""

    def __init__(self, filename: str, project_root: Path):
        self.filename = filename
        self.project_root = project_root
        self.issues: list[dict[str, Any]] = []
        self.current_function: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """检查函数返回类型"""
        old_function = self.current_function
        self.current_function = node.name

        # 检查返回类型注解
        returns = node.returns
        if returns is None:
            # 没有返回类型注解
            self._check_function_body_for_dict(node)
        elif isinstance(returns, ast.Subscript):
            # 如 dict[str, Any] - 允许
            pass
        elif isinstance(returns, ast.Name) and returns.id in ('dict', 'Dict'):
            # 裸 dict 返回类型
            self.issues.append({
                'line': node.lineno,
                'col': node.col_offset,
                'type': 'bare_dict_return',
                'message': f"函数 '{node.name}' 返回裸 dict，应使用 Pydantic 模型或 dict[str, T]",
                'severity': 'warning'
            })

        self.generic_visit(node)
        self.current_function = old_function

    def _check_function_body_for_dict(self, node: ast.FunctionDef) -> None:
        """检查函数体中返回的字典"""
        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Return) and stmt.value:
                if isinstance(stmt.value, ast.Dict):
                    keys = set()
                    for k in stmt.value.keys:
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            keys.add(k.value)
                    if len(keys) >= 3:  # 多键字典应该使用模型
                        suggested_model = find_matching_model(keys, self.project_root)
                        if suggested_model:
                            self.issues.append({
                                'line': stmt.lineno,
                                'col': stmt.col_offset,
                                'type': 'complex_dict_literal',
                                'message': f"返回复杂字典，建议使用 Pydantic 模型: {suggested_model}",
                                'details': f"键名: {sorted(keys)}",
                                'severity': 'suggestion'
                            })
                        else:
                            self.issues.append({
                                'line': stmt.lineno,
                                'col': stmt.col_offset,
                                'type': 'complex_dict_literal',
                                'message': f"返回复杂字典字面量（{len(keys)} 个键），建议定义 Pydantic 模型",
                                'details': f"键名: {sorted(keys)}",
                                'severity': 'suggestion'
                            })

    def visit_Dict(self, node: ast.Dict) -> None:
        """检查字典字面量，提供具体的模型替换建议"""
        # 提取字典键名
        keys = set()
        for k in node.keys:
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                keys.add(k.value)

        if not keys:
            self.generic_visit(node)
            return

        # 尝试匹配 Pydantic 模型
        suggested_model = find_matching_model(keys, self.project_root)

        if suggested_model:
            self.issues.append({
                'line': node.lineno,
                'col': node.col_offset,
                'type': 'metadata_dict_literal',
                'message': f"发现元数据字典，建议使用 Pydantic 模型: {suggested_model}",
                'details': f"当前键名: {sorted(keys)}",
                'suggested_import': f"from backend.domain.models.schemas import {suggested_model}",
                'severity': 'warning'
            })
        elif len(keys) >= 4:  # 复杂字典但没有匹配到模型
            self.issues.append({
                'line': node.lineno,
                'col': node.col_offset,
                'type': 'complex_dict_literal',
                'message': f"复杂字典字面量（{len(keys)} 个键），建议定义 Pydantic 模型",
                'details': f"键名: {sorted(keys)}",
                'severity': 'suggestion'
            })

        self.generic_visit(node)


def check_file(filepath: Path, project_root: Path) -> list[dict]:
    """检查单个文件"""
    try:
        source = filepath.read_text(encoding='utf-8')
        tree = ast.parse(source)
    except SyntaxError as e:
        return [{'line': e.lineno, 'message': f'语法错误: {e}', 'severity': 'error'}]
    except Exception as e:
        return [{'line': 0, 'message': f'读取错误: {e}', 'severity': 'error'}]

    checker = BareDictChecker(str(filepath), project_root)
    checker.visit(tree)
    return checker.issues


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python check_bare_dicts.py <目录或文件>")
        return 1

    target = Path(sys.argv[1])
    project_root = Path.cwd()

    files = []
    if target.is_file():
        files = [target]
    else:
        files = list(target.rglob('*.py'))

    # 预加载 schemas
    suggestions = get_model_suggestions(project_root)
    if suggestions:
        print(f"已加载 {len(suggestions)} 个 Pydantic 模型定义:")
        for fields, model in list(suggestions.items())[:3]:
            print(f"  - {model}: {len(fields)} 个字段")
        if len(suggestions) > 3:
            print(f"  ... 还有 {len(suggestions) - 3} 个")
        print()

    total_issues = 0
    for filepath in files:
        if 'venv' in str(filepath) or '__pycache__' in str(filepath):
            continue

        issues = check_file(filepath, project_root)
        if issues:
            total_issues += len(issues)
            print(f"\n{filepath}:")
            for issue in issues:
                severity = issue.get('severity', 'info').upper()
                print(f"  行 {issue['line']}: [{severity}] {issue['message']}")
                if 'details' in issue:
                    print(f"           {issue['details']}")
                if 'suggested_import' in issue:
                    print(f"           建议: {issue['suggested_import']}")

    print(f"\n{'='*50}")
    print(f"总计: {total_issues} 个问题")
    return 0 if total_issues == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
