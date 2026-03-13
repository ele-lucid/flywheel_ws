"""Validates LLM-generated mission code before execution."""

import ast
import builtins
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
    'getattr', 'setattr', 'delattr',  # Attribute access bypass
    'globals', 'locals', 'vars',  # Namespace access
    'breakpoint',  # Debugger
    'input',  # Blocks execution
    '__builtins__',  # Access to builtins
    'importlib',  # Dynamic import bypass
}

BANNED_DUNDER_ATTRS = {
    '__import__', '__subclasses__', '__class__', '__bases__', '__mro__',
}

# Names that should not be used as mission class names
_BUILTIN_NAMES = set(dir(builtins))
_SHADOWED_MODULES = {
    'math', 'time', 'json', 'numpy', 'os', 'sys', 'ast', 'typing',
    'collections', 'functools', 'itertools', 'logging', 'rclpy',
}


@dataclass
class ValidationResult:
    ok: bool = True
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def fail(self, msg):
        self.ok = False
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


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

    # 4. Check for banned dunder attribute access (sandbox escape techniques)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if node.attr in BANNED_DUNDER_ATTRS:
                result.fail(f'Banned attribute access: {node.attr}')

    # 5. Check that there is a class inheriting from BaseMission
    has_mission_class = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = _get_name(base)
                if 'BaseMission' in base_name:
                    has_mission_class = True
                    # Check class name does not shadow builtins or common modules
                    if node.name in _BUILTIN_NAMES:
                        result.fail(
                            f'Class name "{node.name}" shadows a Python builtin. Choose a different name.'
                        )
                    elif node.name in _SHADOWED_MODULES:
                        result.fail(
                            f'Class name "{node.name}" shadows a common module. Choose a different name.'
                        )
                    # Check it has an execute method
                    has_execute = any(
                        isinstance(item, ast.FunctionDef) and item.name == 'execute'
                        for item in node.body
                    )
                    if not has_execute:
                        result.fail(f'Class {node.name} must override execute() method')

    if not has_mission_class:
        result.fail('No class inheriting from BaseMission found')

    # 6. Check for time.sleep calls (should use ROS timers instead)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _get_call_name(node)
            if call_name == 'time.sleep':
                result.fail('Do not use time.sleep(). The execute() method is called at 10Hz by the base class timer.')

    # 7. Detect infinite loops: while True without a break
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            if _is_while_true(node) and not _has_break(node):
                result.warn(
                    'Potential infinite loop detected. Use state machine pattern instead.'
                )

    # 8. Detect recursive calls
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if _calls_itself(node):
                result.warn(
                    f'Recursive call detected in "{node.name}". Ensure base case exists.'
                )

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


def _is_while_true(node):
    """Check if a While node is `while True`."""
    test = node.test
    if isinstance(test, ast.Constant) and test.value is True:
        return True
    if isinstance(test, ast.NameConstant) and getattr(test, 'value', None) is True:
        return True
    return False


def _has_break(node):
    """Check if a loop body contains a break statement (not in nested loops)."""
    for child in ast.walk(node):
        if child is node:
            continue
        # Don't descend into nested loops
        if isinstance(child, (ast.For, ast.While)) and child is not node:
            continue
        if isinstance(child, ast.Break):
            return True
    return False


def _calls_itself(func_node):
    """Check if a FunctionDef contains a call to itself."""
    name = func_node.name
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            call_name = _get_call_name(node)
            # Match direct call (foo()) or method call via self (self.foo())
            if call_name == name or call_name == f'self.{name}':
                return True
    return False
