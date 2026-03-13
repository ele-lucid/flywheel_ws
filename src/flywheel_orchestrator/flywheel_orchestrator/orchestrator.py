"""The Flywheel: Perceive -> Reason -> Act -> Learn, forever.

This is the stable kernel. The LLM never modifies this file.
It only modifies mission nodes in flywheel_missions/generated/.
"""

import json
import os
import signal
import statistics
import subprocess
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from std_msgs.msg import String, Empty

from .llm_client import LLMClient
from .code_writer import CodeWriter
from .code_validator import validate_mission_code
from .mission_runner import MissionRunner
from .evaluator import evaluate_mission
from .log_analyzer import LogAnalyzer, LessonStore, CodeHistory


def load_env(filepath):
    """Load key=value pairs from a .env file."""
    if not os.path.exists(filepath):
        return
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())


class Orchestrator(Node):
    def __init__(self):
        super().__init__('flywheel_orchestrator')

        # Paths
        self.ws_path = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))))
        # Go up to workspace root (from src/flywheel_orchestrator/flywheel_orchestrator/)
        # Actually, let's just use a parameter or find it
        self.declare_parameter('workspace', '')
        ws = self.get_parameter('workspace').get_parameter_value().string_value
        if ws:
            self.ws_path = ws
        else:
            # Auto-detect: walk up from this file until we find flywheel.env
            p = os.path.abspath(__file__)
            for _ in range(10):
                p = os.path.dirname(p)
                if os.path.exists(os.path.join(p, 'flywheel.env')):
                    self.ws_path = p
                    break

        self.logs_path = os.path.join(self.ws_path, 'logs')
        self.memory_path = os.path.join(self.ws_path, 'memory')
        os.makedirs(self.logs_path, exist_ok=True)
        os.makedirs(self.memory_path, exist_ok=True)

        # Load config
        load_env(os.path.join(self.ws_path, 'flywheel.env'))

        # Components
        self.llm = LLMClient()
        self.code_writer = CodeWriter(self.llm)
        self.mission_runner = MissionRunner(
            self.ws_path,
            timeout=int(os.environ.get('MISSION_TIMEOUT_SEC', '120'))
        )
        self.log_analyzer = LogAnalyzer(self.llm)
        self.lessons = LessonStore(os.path.join(self.memory_path, 'lessons.jsonl'))
        self.code_history = CodeHistory(os.path.join(self.memory_path, 'code_history.jsonl'))

        self.max_llm_calls = int(os.environ.get('MAX_LLM_CALLS_PER_CYCLE', '20'))
        self.failure_threshold = int(os.environ.get('FAILURE_RESET_THRESHOLD', '3'))

        # QoS profiles
        world_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )
        status_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        reset_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # World model subscriber
        self._world_state = None
        self._world_state_time = 0
        self.world_sub = self.create_subscription(
            String, '/perception/world_model', self._world_cb, world_qos)

        # Mission status subscriber
        self._mission_status = None
        self.status_sub = self.create_subscription(
            String, '/mission/status', self._status_cb, status_qos)

        # Reset publisher (to reset goals_visited in world_model)
        self.reset_pub = self.create_publisher(Empty, '/flywheel/reset', reset_qos)

        # Determine starting cycle
        self.cycle = self._find_last_cycle() + 1
        self._recent_scores = []  # Rolling window for failure detection

        self.get_logger().info(f'Flywheel orchestrator initialized. Starting at cycle {self.cycle}')
        self.get_logger().info(f'Workspace: {self.ws_path}')
        self.get_logger().info(f'LLM: {self.llm.model} @ {self.llm.base_url}')

    def _world_cb(self, msg):
        try:
            self._world_state = json.loads(msg.data)
            self._world_state_time = time.time()
        except json.JSONDecodeError as e:
            self.get_logger().error(f'Failed to parse world model JSON: {e}')

    def _status_cb(self, msg):
        try:
            self._mission_status = json.loads(msg.data)
        except json.JSONDecodeError as e:
            self.get_logger().error(f'Failed to parse mission status JSON: {e}')

    def _find_last_cycle(self):
        """Find the highest cycle number in logs/."""
        max_cycle = 0
        if os.path.exists(self.logs_path):
            for name in os.listdir(self.logs_path):
                if name.startswith('cycle_'):
                    try:
                        n = int(name.split('_')[1])
                        max_cycle = max(max_cycle, n)
                    except ValueError:
                        pass
        return max_cycle

    def wait_for_world_model(self, timeout=30):
        """Spin until we get a fresh world model."""
        self.get_logger().info('Waiting for world model...')
        start = time.time()
        while time.time() - start < timeout:
            rclpy.spin_once(self, timeout_sec=0.5)
            if self._world_state and (time.time() - self._world_state_time) < 2.0:
                return self._world_state
        self.get_logger().warn('Timed out waiting for world model')
        return None

    def _spin_aware_execute(self, module_name, log_dir):
        """Run mission subprocess with polling loop so callbacks keep firing."""
        from .mission_runner import MissionResult
        result = MissionResult()
        runner = self.mission_runner
        workspace = runner.workspace_path
        timeout = runner.timeout

        # Open sensor log for recording world model during execution
        sensor_log_path = os.path.join(log_dir, 'sensor_log.jsonl') if log_dir else None
        sensor_log_file = None
        if sensor_log_path:
            os.makedirs(log_dir, exist_ok=True)
            sensor_log_file = open(sensor_log_path, 'w')
        last_log_time = 0

        cmd = [
            sys.executable, '-c',
            f"""
import sys
sys.path.insert(0, '{os.path.join(workspace, "src", "flywheel_missions")}')
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

        env = os.environ.copy()
        pythonpath = os.path.join(workspace, 'src', 'flywheel_missions')
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
                preexec_fn=os.setsid,
            )

            # Poll instead of blocking on communicate()
            while proc.poll() is None:
                rclpy.spin_once(self, timeout_sec=0.1)

                # Log world model state at ~5Hz for coverage evaluation
                now = time.time()
                if sensor_log_file and self._world_state and (now - last_log_time) >= 0.2:
                    sensor_log_file.write(json.dumps(self._world_state) + '\n')
                    last_log_time = now

                if time.time() - start_time > timeout:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    time.sleep(2)
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    result.timed_out = True
                    break

            stdout, stderr = proc.communicate(timeout=5)
            result.exit_code = proc.returncode
            result.stdout = stdout.decode('utf-8', errors='replace')
            result.stderr = stderr.decode('utf-8', errors='replace')

        except Exception as e:
            result.exit_code = -1
            result.stderr = str(e)
            result.crashed = True

        result.duration = time.time() - start_time

        # Close sensor log
        if sensor_log_file:
            sensor_log_file.flush()
            sensor_log_file.close()

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

    def run_flywheel(self):
        """The main loop. Runs forever."""
        self.get_logger().info('=== FLYWHEEL STARTED ===')

        while rclpy.ok():
            try:
                self._run_cycle()
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.get_logger().error(f'Cycle {self.cycle} failed with exception: {e}')
                import traceback
                traceback.print_exc()
                self.cycle += 1
                time.sleep(5)

        self.get_logger().info('=== FLYWHEEL STOPPED ===')
        self.get_logger().info(f'LLM stats: {self.llm.get_stats()}')

    def _run_cycle(self):
        cycle = self.cycle
        log_dir = os.path.join(self.logs_path, f'cycle_{cycle:03d}')
        os.makedirs(log_dir, exist_ok=True)

        self.get_logger().info(f'\n{"="*60}')
        self.get_logger().info(f'CYCLE {cycle} BEGIN')
        self.get_logger().info(f'{"="*60}')

        # Reset LLM call counter
        self.llm.call_count = 0

        # Teleport robot to origin via Gazebo and reset world model
        self._reset_robot()
        time.sleep(1)  # Wait for odom to settle after teleport

        # ============================================
        # PHASE 1: PERCEIVE
        # ============================================
        self.get_logger().info('[PERCEIVE] Reading world state...')
        world_state = self.wait_for_world_model(timeout=30)
        if world_state is None:
            self.get_logger().error('No world model available. Is the sim running?')
            self.cycle += 1
            time.sleep(10)
            return

        with open(os.path.join(log_dir, 'world_model.json'), 'w') as f:
            json.dump(world_state, f, indent=2)

        self.get_logger().info(f'  Position: ({world_state["pose"]["x"]}, {world_state["pose"]["y"]})')
        self.get_logger().info(f'  Goals remaining: {len(world_state.get("goals_remaining", []))}')

        # ============================================
        # PHASE 2: REASON
        # ============================================
        self.get_logger().info('[REASON] Planning mission...')

        # Gather context
        current_lessons = self.lessons.load(max_lessons=15)
        best_score, best_code_path = self.code_history.get_best()
        best_code = None
        if best_code_path and os.path.exists(best_code_path):
            with open(best_code_path) as f:
                best_code = f.read()

        last_eval = None
        last_log_dir = os.path.join(self.logs_path, f'cycle_{cycle-1:03d}')
        eval_path = os.path.join(last_log_dir, 'evaluation.json')
        if os.path.exists(eval_path):
            with open(eval_path) as f:
                last_eval = json.load(f)

        # Ask LLM for mission plan
        reason_prompt = self._build_reason_prompt(world_state, current_lessons, last_eval, best_score)
        mission_plan = self.llm.chat(
            "You are a mission planner for a differential drive robot in a 20x20m arena with obstacles. "
            "The PRIMARY OBJECTIVE is FULL AREA COVERAGE: visit every square meter of the arena floor. "
            "Use systematic coverage patterns (lawnmower/boustrophedon, spiral, wall-following). "
            "Avoid revisiting areas already covered. Track coverage progress via visited grid cells. "
            "Secondary: visit goal markers when they are along the coverage path. "
            "Be concise, 3-5 sentences.",
            reason_prompt,
            temperature=0.7
        )

        # Null propagation safety: skip cycle if LLM returned None
        if mission_plan is None:
            self.get_logger().warn('LLM returned None for mission plan. Skipping cycle.')
            self.cycle += 1
            return

        with open(os.path.join(log_dir, 'mission_plan.txt'), 'w') as f:
            f.write(mission_plan)
        self.get_logger().info(f'  Plan: {mission_plan[:200]}...')

        # ============================================
        # PHASE 3: ACT
        # ============================================
        self.get_logger().info('[ACT] Generating mission code...')

        world_state_str = json.dumps(world_state, indent=2)
        code, validation = self.code_writer.generate_and_validate(
            world_state_str, mission_plan, best_code, current_lessons)

        # Null propagation safety: skip cycle if code generation returned None
        if code is None:
            self.get_logger().warn('Code generation returned None. Skipping cycle.')
            self.cycle += 1
            return

        if not validation.ok:
            self.get_logger().error(f'Code validation failed after retries: {validation.errors}')
            with open(os.path.join(log_dir, 'failed_code.py'), 'w') as f:
                f.write(code)
            with open(os.path.join(log_dir, 'validation_errors.json'), 'w') as f:
                json.dump(validation.errors, f, indent=2)
            self._record_score(0)
            self.cycle += 1
            return

        # Save the code
        code_path, module_name = self.mission_runner.save_mission_code(code, cycle)
        with open(os.path.join(log_dir, 'generated_code.py'), 'w') as f:
            f.write(code)

        self.get_logger().info(f'  Saved: {module_name} ({len(code)} bytes)')
        self.get_logger().info(f'  Running mission (timeout={self.mission_runner.timeout}s)...')

        # Execute with spin-aware polling
        mission_result = self._spin_aware_execute(module_name, log_dir=log_dir)

        self.get_logger().info(f'  Duration: {mission_result.duration:.1f}s')
        self.get_logger().info(f'  Exit code: {mission_result.exit_code}')
        self.get_logger().info(f'  Timed out: {mission_result.timed_out}')
        self.get_logger().info(f'  Crashed: {mission_result.crashed}')

        # ============================================
        # PHASE 4: LEARN
        # ============================================
        self.get_logger().info('[LEARN] Evaluating and analyzing...')

        sensor_log = os.path.join(log_dir, 'sensor_log.jsonl')
        evaluation = evaluate_mission(mission_result, sensor_log)

        with open(os.path.join(log_dir, 'evaluation.json'), 'w') as f:
            json.dump(evaluation, f, indent=2)

        self.get_logger().info(f'  Score: {evaluation["total_score"]}/100')
        self.get_logger().info(f'  Goals: {evaluation["details"]["goals_visited"]}')
        self.get_logger().info(f'  Collisions: {evaluation["details"]["collision_count"]}')

        # LLM analysis
        if self.llm.call_count < self.max_llm_calls:
            analysis = self.log_analyzer.analyze(
                code, evaluation, sensor_log,
                mission_result.stdout, mission_result.stderr)

            # Null propagation safety: use safe default if analysis is None
            if analysis is None:
                self.get_logger().warn('Log analysis returned None. Using safe defaults.')
                analysis = {
                    'failure_modes': [],
                    'success_factors': [],
                    'root_causes': [],
                    'lessons': [],
                    'next_strategy': 'Retry previous approach',
                }

            with open(os.path.join(log_dir, 'analysis.json'), 'w') as f:
                json.dump(analysis, f, indent=2)

            # Store lessons
            new_lessons = analysis.get('lessons', [])
            if new_lessons:
                self.lessons.add(new_lessons, cycle)
                self.get_logger().info(f'  New lessons: {len(new_lessons)}')
                for l in new_lessons:
                    self.get_logger().info(f'    - {l}')

        # Update code history
        self.code_history.add(cycle, evaluation['total_score'], code_path)

        # Track score in rolling window and check for bad streak
        score = evaluation['total_score']
        self._record_score(score)

        # Check if new best
        if score > best_score:
            best_path = os.path.join(self.memory_path, 'best_mission.py')
            with open(best_path, 'w') as f:
                f.write(code)
            self.get_logger().info(f'  NEW BEST! {score} > {best_score}')

        # Cycle summary
        self.get_logger().info(f'\nCYCLE {cycle} COMPLETE')
        self.get_logger().info(f'  Score: {score}/100 (best: {max(best_score, score)})')
        self.get_logger().info(f'  LLM calls: {self.llm.call_count}, tokens: {self.llm.total_tokens}')
        self.get_logger().info(f'  Recent scores: {self._recent_scores}')

        # Save conversation log
        with open(os.path.join(log_dir, 'cycle_summary.json'), 'w') as f:
            json.dump({
                'cycle': cycle,
                'score': score,
                'llm_calls': self.llm.call_count,
                'llm_tokens': self.llm.total_tokens,
                'mission_plan': mission_plan,
                'duration': mission_result.duration,
            }, f, indent=2)

        self.cycle += 1

        # Brief pause before next cycle
        self.get_logger().info('Pausing 5s before next cycle...')
        time.sleep(5)

    def _record_score(self, score):
        """Add score to rolling window and trigger lesson reset if median is too low."""
        self._recent_scores.append(score)
        # Keep only the last 5 scores
        if len(self._recent_scores) > 5:
            self._recent_scores = self._recent_scores[-5:]

        # Only evaluate once we have a full window
        if len(self._recent_scores) >= 5:
            median_score = statistics.median(self._recent_scores)
            if median_score < 20:
                self.get_logger().warn(
                    f'Rolling median score {median_score:.1f} is below threshold (20). '
                    f'Recent scores: {self._recent_scores}. '
                    f'Clearing recent lessons and resetting to best code.')
                self.lessons.clear_recent(n=10)
                self._recent_scores.clear()

    def _reset_robot(self):
        """Teleport robot to origin via Gazebo service and reset world model."""
        try:
            result = subprocess.run(
                ['gz', 'service', '-s', '/world/flywheel_arena/set_pose',
                 '--reqtype', 'gz.msgs.Pose',
                 '--reptype', 'gz.msgs.Boolean',
                 '--req',
                 'name: "flywheel_bot", position: {x: 0, y: 0, z: 0.05}, '
                 'orientation: {x: 0, y: 0, z: 0, w: 1}',
                 '--timeout', '5000'],
                capture_output=True, text=True, timeout=10
            )
            if 'true' in result.stdout:
                self.get_logger().info('Robot teleported to origin')
            else:
                self.get_logger().warn(f'Set pose response: {result.stdout} {result.stderr}')
        except Exception as e:
            self.get_logger().warn(f'Failed to reset robot pose: {e}')

        # Reset world model (clears goals_visited and sets odom offset)
        self.reset_pub.publish(Empty())
        self.get_logger().info('Published reset to world model')

    def _build_reason_prompt(self, world_state, lessons, last_eval, best_score):
        parts = []
        parts.append(f"## Current World State\n```json\n{json.dumps(world_state, indent=2)}\n```\n")

        if last_eval:
            parts.append(f"## Last Mission Score: {last_eval.get('total_score', 0)}/100\n")
            parts.append(f"Goals reached: {last_eval.get('details', {}).get('goals_visited', [])}\n")
            parts.append(f"Collisions: {last_eval.get('details', {}).get('collision_count', 0)}\n")
            if last_eval.get('details', {}).get('crashed'):
                parts.append("Last mission CRASHED.\n")

        parts.append(f"## Best Score So Far: {best_score}/100\n")

        if lessons:
            parts.append("## Lessons Learned (most recent):\n")
            for l in lessons[-10:]:
                parts.append(f"- {l}\n")

        parts.append(
            "\n## Task\n"
            "Produce a COVERAGE-FOCUSED mission plan. Be specific about:\n"
            "1. Coverage pattern (lawnmower rows, spiral, wall-follow-then-fill)\n"
            "2. How to systematically sweep unvisited areas (track visited cells as 1m grid)\n"
            "3. Obstacle avoidance while maintaining coverage pattern\n"
            "4. What to do differently from last time to increase cells_visited count\n"
            f"Arena is 20x20m (-10 to 10 on each axis). Target: cover all {350} reachable cells.\n"
        )
        return '\n'.join(parts)


def main(args=None):
    rclpy.init(args=args)
    orchestrator = Orchestrator()

    try:
        orchestrator.run_flywheel()
    except KeyboardInterrupt:
        pass
    finally:
        orchestrator.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
