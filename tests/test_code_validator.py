"""Tests for the AST-based code validator."""

from flywheel_orchestrator.code_validator import validate_mission_code


GOOD_CODE = '''
import math
from flywheel_missions.base_mission import BaseMission

class MyMission(BaseMission):
    def __init__(self):
        super().__init__('my_mission')
        self.state = 'SEEK'

    def execute(self):
        world = self.get_world_state()
        if world is None:
            return
        self.move_forward(0.3)
'''

GOOD_CODE_WITH_NUMPY = '''
import math
import numpy as np
from flywheel_missions.base_mission import BaseMission

class NumpyMission(BaseMission):
    def __init__(self):
        super().__init__('numpy_mission')

    def execute(self):
        world = self.get_world_state()
        if world is None:
            return
        arr = np.array([1.0, 2.0])
        self.move_forward(float(np.mean(arr)))
'''


class TestValidCode:
    def test_basic_valid_mission(self):
        result = validate_mission_code(GOOD_CODE)
        assert result.ok
        assert result.errors == []

    def test_valid_with_numpy(self):
        result = validate_mission_code(GOOD_CODE_WITH_NUMPY)
        assert result.ok

    def test_valid_with_json_import(self):
        code = GOOD_CODE.replace('import math', 'import math\nimport json')
        result = validate_mission_code(code)
        assert result.ok


class TestBannedImports:
    def test_os_import(self):
        code = GOOD_CODE.replace('import math', 'import os')
        result = validate_mission_code(code)
        assert not result.ok
        assert any('Banned import' in e for e in result.errors)

    def test_subprocess_import(self):
        code = GOOD_CODE.replace('import math', 'import subprocess')
        result = validate_mission_code(code)
        assert not result.ok

    def test_socket_import(self):
        code = GOOD_CODE.replace('import math', 'import socket')
        result = validate_mission_code(code)
        assert not result.ok

    def test_from_os_import(self):
        code = GOOD_CODE.replace('import math', 'from os import path')
        result = validate_mission_code(code)
        assert not result.ok


class TestBannedCalls:
    def test_exec_call(self):
        code = GOOD_CODE.replace('self.move_forward(0.3)', 'exec("print(1)")')
        result = validate_mission_code(code)
        assert not result.ok
        assert any('Banned function call' in e for e in result.errors)

    def test_eval_call(self):
        code = GOOD_CODE.replace('self.move_forward(0.3)', 'eval("1+1")')
        result = validate_mission_code(code)
        assert not result.ok

    def test_open_call(self):
        code = GOOD_CODE.replace('self.move_forward(0.3)', 'open("/etc/passwd")')
        result = validate_mission_code(code)
        assert not result.ok

    def test_os_system_call(self):
        code = GOOD_CODE.replace('import math', 'import math').replace(
            'self.move_forward(0.3)', 'os.system("rm -rf /")')
        result = validate_mission_code(code)
        assert not result.ok


class TestSleepBan:
    def test_time_sleep_banned(self):
        code = GOOD_CODE.replace('import math', 'import math\nimport time').replace(
            'self.move_forward(0.3)', 'time.sleep(1)')
        result = validate_mission_code(code)
        assert not result.ok
        assert any('time.sleep' in e for e in result.errors)


class TestClassStructure:
    def test_no_class(self):
        code = '''
import math

def my_function():
    pass
'''
        result = validate_mission_code(code)
        assert not result.ok
        assert any('No class inheriting from BaseMission' in e for e in result.errors)

    def test_class_without_base_mission(self):
        code = '''
class MyClass:
    def execute(self):
        pass
'''
        result = validate_mission_code(code)
        assert not result.ok
        assert any('No class inheriting from BaseMission' in e for e in result.errors)

    def test_class_without_execute(self):
        code = '''
from flywheel_missions.base_mission import BaseMission

class MyMission(BaseMission):
    def __init__(self):
        super().__init__('test')

    def run(self):
        pass
'''
        result = validate_mission_code(code)
        assert not result.ok
        assert any('execute()' in e for e in result.errors)


class TestDunderAttrAccess:
    def test_subclasses_access_banned(self):
        code = GOOD_CODE.replace('self.move_forward(0.3)', 'x = "".__class__.__subclasses__()')
        result = validate_mission_code(code)
        assert not result.ok
        assert any('Banned attribute access' in e for e in result.errors)

    def test_import_dunder_banned(self):
        code = GOOD_CODE.replace('self.move_forward(0.3)', 'x = builtins.__import__("os")')
        result = validate_mission_code(code)
        assert not result.ok


class TestExpandedBannedCalls:
    def test_getattr_banned(self):
        code = GOOD_CODE.replace('self.move_forward(0.3)', 'getattr(self, "stop")()')
        result = validate_mission_code(code)
        assert not result.ok

    def test_globals_banned(self):
        code = GOOD_CODE.replace('self.move_forward(0.3)', 'g = globals()')
        result = validate_mission_code(code)
        assert not result.ok

    def test_breakpoint_banned(self):
        code = GOOD_CODE.replace('self.move_forward(0.3)', 'breakpoint()')
        result = validate_mission_code(code)
        assert not result.ok


class TestWarnings:
    def test_while_true_no_break_warns(self):
        code = GOOD_CODE.replace(
            'self.move_forward(0.3)',
            'while True:\n            self.move_forward(0.1)'
        )
        result = validate_mission_code(code)
        assert len(result.warnings) > 0
        assert any('infinite loop' in w for w in result.warnings)
        # Warnings don't fail validation
        assert result.ok

    def test_while_true_with_break_no_warn(self):
        code = GOOD_CODE.replace(
            'self.move_forward(0.3)',
            'while True:\n            if True:\n                break'
        )
        result = validate_mission_code(code)
        assert not any('infinite loop' in w for w in result.warnings)

    def test_recursion_warns(self):
        code = '''
from flywheel_missions.base_mission import BaseMission

class MyMission(BaseMission):
    def execute(self):
        self.helper()

    def helper(self):
        self.helper()
'''
        result = validate_mission_code(code)
        assert any('Recursive' in w for w in result.warnings)


class TestClassNameValidation:
    def test_builtin_name_rejected(self):
        code = GOOD_CODE.replace('class MyMission', 'class int')
        result = validate_mission_code(code)
        assert not result.ok
        assert any('shadows' in e for e in result.errors)

    def test_module_name_rejected(self):
        code = GOOD_CODE.replace('class MyMission', 'class math')
        result = validate_mission_code(code)
        assert not result.ok
        assert any('shadows' in e for e in result.errors)


class TestEdgeCases:
    def test_syntax_error(self):
        result = validate_mission_code('def foo(:\n  pass')
        assert not result.ok
        assert any('Syntax error' in e for e in result.errors)

    def test_empty_code(self):
        result = validate_mission_code('')
        assert not result.ok
        assert any('No class inheriting from BaseMission' in e for e in result.errors)

    def test_multiple_classes_one_valid(self):
        code = '''
from flywheel_missions.base_mission import BaseMission

class Helper:
    pass

class MyMission(BaseMission):
    def execute(self):
        self.move_forward(0.3)
'''
        result = validate_mission_code(code)
        assert result.ok
