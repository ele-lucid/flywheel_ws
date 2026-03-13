"""Runs a generated mission node as a subprocess with timeout and monitoring."""

import json
import os
import signal
import subprocess
import sys
import time
import threading


class MissionResult:
    def __init__(self):
        self.exit_code = -1
        self.duration = 0.0
        self.stdout = ''
        self.stderr = ''
        self.status_messages = []
        self.timed_out = False
        self.crashed = False


class MissionRunner:
    def __init__(self, workspace_path, timeout=120):
        self.workspace_path = workspace_path
        self.timeout = timeout
        self.missions_pkg_path = os.path.join(
            workspace_path, 'src', 'flywheel_missions', 'flywheel_missions', 'generated')

    def save_mission_code(self, code, version):
        """Save generated code to the missions package."""
        filename = f'mission_v{version:03d}.py'
        filepath = os.path.join(self.missions_pkg_path, filename)
        with open(filepath, 'w') as f:
            f.write(code)
        return filepath, f'mission_v{version:03d}'

    def run_mission(self, module_name, log_dir=None):
        """Run a mission module as a subprocess. Returns MissionResult."""
        result = MissionResult()

        # Build the command - use the Python path directly to avoid colcon rebuild
        cmd = [
            sys.executable, '-c',
            f"""
import sys
sys.path.insert(0, '{os.path.join(self.workspace_path, "src", "flywheel_missions")}')
import rclpy
import importlib
rclpy.init()
mod = importlib.import_module('flywheel_missions.generated.{module_name}')
cls = None
for name in dir(mod):
    obj = getattr(mod, name)
    if isinstance(obj, type) and hasattr(obj, 'execute') and name != 'BaseMission':
        cls = obj
        break
if cls is None:
    print('ERROR: No mission class found', file=sys.stderr)
    sys.exit(1)
node = cls()
try:
    rclpy.spin(node)
except KeyboardInterrupt:
    pass
finally:
    node.destroy_node()
    rclpy.shutdown()
"""
        ]

        # Set up environment
        env = os.environ.copy()
        pythonpath = os.path.join(self.workspace_path, 'src', 'flywheel_missions')
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = pythonpath + ':' + env['PYTHONPATH']
        else:
            env['PYTHONPATH'] = pythonpath

        start_time = time.time()

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                preexec_fn=os.setsid,  # Create process group for clean kill
            )

            # Monitor with timeout
            try:
                stdout, stderr = proc.communicate(timeout=self.timeout)
                result.exit_code = proc.returncode
                result.stdout = stdout.decode('utf-8', errors='replace')
                result.stderr = stderr.decode('utf-8', errors='replace')
            except subprocess.TimeoutExpired:
                # Kill the entire process group
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                time.sleep(2)
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout, stderr = proc.communicate(timeout=5)
                result.exit_code = -1
                result.stdout = stdout.decode('utf-8', errors='replace')
                result.stderr = stderr.decode('utf-8', errors='replace')
                result.timed_out = True

        except Exception as e:
            result.exit_code = -1
            result.stderr = str(e)
            result.crashed = True

        result.duration = time.time() - start_time

        if result.exit_code != 0 and not result.timed_out:
            result.crashed = True

        # Save logs
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, 'mission_stdout.txt'), 'w') as f:
                f.write(result.stdout)
            with open(os.path.join(log_dir, 'mission_stderr.txt'), 'w') as f:
                f.write(result.stderr)

        return result
