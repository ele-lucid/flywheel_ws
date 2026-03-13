"""The Flywheel: Perceive -> Reason -> Act -> Learn, forever.

This is the stable kernel. The LLM never modifies this file.
It only modifies mission nodes in flywheel_missions/generated/.
"""

import json
import os
import signal
import subprocess
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

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

        # World model subscriber
        self._world_state = None
        self._world_state_time = 0
        self.world_sub = self.create_subscription(
            String, '/perception/world_model', self._world_cb, 10)

        # Mission status subscriber
        self._mission_status = None
        self.status_sub = self.create_subscription(
            String, '/mission/status', self._status_cb, 10)

        # Determine starting cycle
        self.cycle = self._find_last_cycle() + 1
        self.consecutive_failures = 0

        self.get_logger().info(f'Flywheel orchestrator initialized. Starting at cycle {self.cycle}')
        self.get_logger().info(f'Workspace: {self.ws_path}')
        self.get_logger().info(f'LLM: {self.llm.model} @ {self.llm.base_url}')

    def _world_cb(self, msg):
        self._world_state = json.loads(msg.data)
        self._world_state_time = time.time()

    def _status_cb(self, msg):
        self._mission_status = json.loads(msg.data)

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
            "You are a mission planner for a differential drive robot navigating an obstacle arena. "
            "Given the world state and lessons, produce a clear, specific mission plan. "
            "Focus on: which goals to target, navigation strategy, obstacle avoidance approach. "
            "Be concise, 3-5 sentences.",
            reason_prompt,
            temperature=0.7
        )

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

        if not validation.ok:
            self.get_logger().error(f'Code validation failed after retries: {validation.errors}')
            with open(os.path.join(log_dir, 'failed_code.py'), 'w') as f:
                f.write(code)
            with open(os.path.join(log_dir, 'validation_errors.json'), 'w') as f:
                json.dump(validation.errors, f, indent=2)
            self.consecutive_failures += 1
            self.cycle += 1
            return

        # Save the code
        code_path, module_name = self.mission_runner.save_mission_code(code, cycle)
        with open(os.path.join(log_dir, 'generated_code.py'), 'w') as f:
            f.write(code)

        self.get_logger().info(f'  Saved: {module_name} ({len(code)} bytes)')
        self.get_logger().info(f'  Running mission (timeout={self.mission_runner.timeout}s)...')

        # Execute
        mission_result = self.mission_runner.run_mission(module_name, log_dir=log_dir)

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

        # Check if new best
        if evaluation['total_score'] > best_score:
            best_path = os.path.join(self.memory_path, 'best_mission.py')
            with open(best_path, 'w') as f:
                f.write(code)
            self.get_logger().info(f'  NEW BEST! {evaluation["total_score"]} > {best_score}')
            self.consecutive_failures = 0
        elif evaluation['total_score'] < 10:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0

        # Check for bad streak - reset if needed
        if self.consecutive_failures >= self.failure_threshold:
            self.get_logger().warn(
                f'  {self.consecutive_failures} consecutive failures. '
                f'Clearing recent lessons and resetting to best code.')
            self.lessons.clear_recent(n=self.consecutive_failures * 2)
            self.consecutive_failures = 0

        # Cycle summary
        self.get_logger().info(f'\nCYCLE {cycle} COMPLETE')
        self.get_logger().info(f'  Score: {evaluation["total_score"]}/100 (best: {max(best_score, evaluation["total_score"])})')
        self.get_logger().info(f'  LLM calls: {self.llm.call_count}, tokens: {self.llm.total_tokens}')

        # Save conversation log
        with open(os.path.join(log_dir, 'cycle_summary.json'), 'w') as f:
            json.dump({
                'cycle': cycle,
                'score': evaluation['total_score'],
                'llm_calls': self.llm.call_count,
                'llm_tokens': self.llm.total_tokens,
                'mission_plan': mission_plan,
                'duration': mission_result.duration,
            }, f, indent=2)

        self.cycle += 1

        # Brief pause before next cycle
        self.get_logger().info('Pausing 5s before next cycle...')
        time.sleep(5)

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
            "Produce a mission plan. Be specific about:\n"
            "1. Which goals to visit and in what order\n"
            "2. Navigation strategy (direct approach, wall-following, etc.)\n"
            "3. Obstacle avoidance behavior\n"
            "4. What to do differently from last time\n"
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
