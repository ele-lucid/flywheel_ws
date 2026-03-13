"""Validates LLM-generated mission code before execution."""

import ast
import sys
from dataclasses import dataclass, field


ALLOWED_IMPORTS = {
    'math', 'time', 'json', 'numpy', 'np',
    'rclpy', 'rclpy.node',
    'geometry_msgs', 'geometry_msgs.msg',
    'std_msgs', 'std_msgs.msg',
    'nav_msgs', 'nav_msgs.msg',
    'sensor_msgs', 'sensor_msgs.msg',
    'flywheel_missions.base_mission',
}

BANNED_CALLS = {
    'exec', 'eval', 'compile', '__import__',
    'subprocess', 'os.system', 'os.popen',
    'open',  # No file I/O from missions
}


@dataclass
class ValidationResult:
    ok: bool = True
    errors: list = field(default_factory=list)

    def fail(self, msg):
        self.ok = False
        self.errors.append(msg)


def validate_mission_code(code: str) -> ValidationResult:
    """Validate generated Python code. Returns ValidationResult."""
    result = ValidationResult()

    # 1. Syntax check
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        result.fail(f'Syntax error at line {e.lineno}: {e.msg}')
        return result

    # 2. Check imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_root = alias.name.split('.')[0]
                if alias.name not in ALLOWED_IMPORTS and module_root not in ALLOWED_IMPORTS:
                    result.fail(f'Banned import: {alias.name}. Allowed: {sorted(ALLOWED_IMPORTS)}')

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_root = node.module.split('.')[0]
                if node.module not in ALLOWED_IMPORTS and module_root not in ALLOWED_IMPORTS:
                    result.fail(f'Banned import: from {node.module}. Allowed: {sorted(ALLOWED_IMPORTS)}')

    # 3. Check for banned function calls
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _get_call_name(node)
            if call_name in BANNED_CALLS:
                result.fail(f'Banned function call: {call_name}')

    # 4. Check that there is a class inheriting from BaseMission
    has_mission_class = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = _get_name(base)
                if 'BaseMission' in base_name:
                    has_mission_class = True
                    # Check it has an execute method
                    has_execute = any(
                        isinstance(item, ast.FunctionDef) and item.name == 'execute'
                        for item in node.body
                    )
                    if not has_execute:
                        result.fail(f'Class {node.name} must override execute() method')

    if not has_mission_class:
        result.fail('No class inheriting from BaseMission found')

    # 5. Check for time.sleep calls (should use ROS timers instead)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _get_call_name(node)
            if call_name == 'time.sleep':
                result.fail('Do not use time.sleep(). The execute() method is called at 10Hz by the base class timer.')

    return result


def _get_call_name(node):
    """Extract the full dotted name of a function call."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    elif isinstance(node.func, ast.Attribute):
        parts = []
        current = node.func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return '.'.join(reversed(parts))
    return ''


def _get_name(node):
    """Extract name from an AST node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f'{_get_name(node.value)}.{node.attr}'
    return ''
