"""Seed mission: simple reactive goal-seeking with obstacle avoidance.

This is the starting point. The LLM will iterate and improve from here.
"""

import math
from flywheel_missions.base_mission import BaseMission


class MissionV001(BaseMission):
    def __init__(self):
        super().__init__('mission_v001')
        self.state = 'SEEK_GOAL'
        self.avoid_counter = 0
        self.stuck_counter = 0

    def execute(self):
        world = self.get_world_state()
        if world is None:
            return

        # Check if all goals visited
        if len(world.get('goals_remaining', [])) == 0:
            self.complete('SUCCESS')
            return

        # Timeout at 110 seconds
        if self.elapsed_time() > 110:
            self.complete('TIMEOUT')
            return

        obstacles = world.get('obstacles', {})
        front = obstacles.get('front', 99)
        front_left = obstacles.get('front_left', 99)
        front_right = obstacles.get('front_right', 99)

        # Stuck detection
        if world.get('stuck', False):
            self.stuck_counter += 1
            if self.stuck_counter > 20:
                self.log_event('STUCK', 'Reversing')
                self.move(linear=-0.2, angular=0.5)
                self.stuck_counter = 0
                return
        else:
            self.stuck_counter = 0

        # Obstacle avoidance takes priority
        if front < 0.6 or front_left < 0.4 or front_right < 0.4:
            self.state = 'AVOID'
            self.avoid_counter = 15

        if self.state == 'AVOID':
            self.avoid_counter -= 1
            if self.avoid_counter <= 0:
                self.state = 'SEEK_GOAL'
            else:
                # Turn away from nearest obstacle
                if front_left < front_right:
                    self.turn(-0.4)  # Turn right
                else:
                    self.turn(0.4)   # Turn left
                return

        # Goal seeking: head toward nearest remaining goal
        goals = world.get('goals_remaining', [])
        if not goals:
            return

        # Find nearest goal
        nearest = min(goals, key=lambda g: self.distance_to(g['x'], g['y']))

        heading_error = self.heading_to(nearest['x'], nearest['y'])
        dist = self.distance_to(nearest['x'], nearest['y'])

        if abs(heading_error) > 20:
            # Need to turn toward goal
            angular = 0.3 if heading_error > 0 else -0.3
            self.move(linear=0.1, angular=angular)
        elif abs(heading_error) > 5:
            # Slight correction while moving
            angular = 0.15 * (1 if heading_error > 0 else -1)
            self.move(linear=0.3, angular=angular)
        else:
            # Heading is good, go forward
            speed = min(0.4, dist * 0.3)
            self.move_forward(max(0.15, speed))

        self.log_event('NAV', f'Goal {nearest["id"]} d={dist:.1f} h={heading_error:.0f}')
