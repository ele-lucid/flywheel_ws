"""LLM-powered code generation for mission nodes."""

import os
from .llm_client import LLMClient
from .code_validator import validate_mission_code

SYSTEM_PROMPT = """You are a ROS2 robotics engineer. You write Python mission nodes for a differential drive robot.

The robot has:
- Lidar (360 degree, 12m range)
- Depth camera (front-facing, 60 degree FOV)
- IMU (orientation, angular velocity)
- Differential drive (max 0.5 m/s linear, 1.0 rad/s angular)

You write classes that inherit from BaseMission. The execute() method is called at 10Hz.
You must NOT use time.sleep(). Use state machines or counters instead.
Keep code simple and reactive. Avoid complex planning algorithms.

Available BaseMission methods:
- self.get_world_state() -> dict or None
  Returns: {
    "pose": {"x": float, "y": float, "heading_deg": float},
    "velocity": {"linear": float, "angular": float},
    "obstacles": {"front": float, "front_left": float, "left": float, "back_left": float,
                  "back": float, "back_right": float, "right": float, "front_right": float},
    "depth": {"closest": float, "mean": float, "obstacle_fraction": float},
    "imu": {"heading_deg": float, "roll_deg": float, "pitch_deg": float, "stuck": bool},
    "stuck": bool,
    "goals_visited": [int, ...],
    "goals_remaining": [{"id": int, "x": float, "y": float}, ...],
    "goals_total": int
  }
  Obstacle distances are in meters. 99.0 means no obstacle detected.

- self.move_forward(speed=0.3) - Move forward (capped at 0.5 m/s)
- self.move(linear=0.0, angular=0.0) - Move with both linear and angular
- self.turn(angular_vel=0.3) - Turn in place (positive=left, negative=right)
- self.stop() - Stop all motion
- self.heading_to(x, y) -> float - Heading error in degrees to target (positive=turn left)
- self.distance_to(x, y) -> float - Distance in meters to target
- self.elapsed_time() -> float - Seconds since mission start
- self.log_event(event_type, detail) - Log a mission event
- self.complete(status='SUCCESS') - Signal mission completion

ROBOT_WIDTH = 0.34 meters

Rules:
1. Always check get_world_state() is not None before using it
2. Always check obstacle distances before moving forward
3. Use self.complete() when all goals are visited or time is up
4. Keep execute() fast - it runs at 10Hz, do not block
5. Use instance variables (self.xxx) for state between execute() calls
6. Import only: math, json, numpy, rclpy, geometry_msgs, std_msgs, flywheel_missions.base_mission
"""


class CodeWriter:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def generate_mission(self, world_state, mission_plan, best_code=None, lessons=None):
        """Generate a new mission node based on the plan and context."""
        prompt_parts = [f"## Current World State\n```json\n{world_state}\n```\n"]
        prompt_parts.append(f"## Mission Plan\n{mission_plan}\n")

        if best_code:
            prompt_parts.append(f"## Best Previous Mission Code (to improve upon)\n```python\n{best_code}\n```\n")

        if lessons:
            prompt_parts.append(f"## Lessons Learned (apply these)\n")
            for lesson in lessons[-10:]:  # Last 10 lessons
                prompt_parts.append(f"- {lesson}\n")

        prompt_parts.append(
            "\n## Task\n"
            "Write a complete Python mission class. Include all necessary imports.\n"
            "The class must inherit from BaseMission and override execute().\n"
            "Use __init__ to set up any state variables (call super().__init__() first).\n"
            "Respond with ONLY the Python code, no explanation."
        )

        user_prompt = '\n'.join(prompt_parts)
        response = self.llm.chat(SYSTEM_PROMPT, user_prompt, temperature=0.7)
        code = self.llm.extract_code(response)
        return code

    def fix_code(self, code, errors, attempt=1):
        """Fix code based on validation errors."""
        prompt = (
            f"## Code with errors\n```python\n{code}\n```\n\n"
            f"## Validation errors\n"
        )
        for e in errors:
            prompt += f"- {e}\n"

        prompt += (
            f"\n## Task (attempt {attempt}/3)\n"
            "Fix all the errors and return the corrected Python code.\n"
            "Respond with ONLY the Python code, no explanation."
        )

        response = self.llm.chat(SYSTEM_PROMPT, prompt, temperature=0.3)
        return self.llm.extract_code(response)

    def generate_and_validate(self, world_state, mission_plan, best_code=None, lessons=None, max_retries=3):
        """Generate code and validate it, retrying on failure."""
        code = self.generate_mission(world_state, mission_plan, best_code, lessons)

        for attempt in range(max_retries):
            result = validate_mission_code(code)
            if result.ok:
                return code, result
            code = self.fix_code(code, result.errors, attempt + 1)

        # Final check
        result = validate_mission_code(code)
        return code, result
