import math
from flywheel_missions.base_mission import BaseMission

class LawnMowerMission(BaseMission):
    def __init__(self):
        super().__init__()
        self.visited_cells = set()
        self.current_waypoint_index = 0
        self.state = 'MOVE_TO_WAYPOINT'
        self.stuck_counter = 0
        self.avoid_counter = 0
        self.recover_counter = 0
        self.generate_waypoints()

    def generate_waypoints(self):
        self.waypoints = [
            (5, 5), (0, -3), (-5, -5), (7, -7), (-8, 7)
        ]
        for y in range(-9, 10):
            if y % 2 == 0:
                for x in range(-9, 10):
                    if (x, y) not in self.waypoints:
                        self.waypoints.append((x, y))
            else:
                for x in range(9, -10, -1):
                    if (x, y) not in self.waypoints:
                        self.waypoints.append((x, y))

    def execute(self):
        world_state = self.get_world_state()
        if world_state is None:
            return

        pose = world_state["pose"]
        current_x, current_y = pose["x"], pose["y"]
        velocity = world_state["velocity"]
        obstacles = world_state["obstacles"]
        stuck = world_state["stuck"]

        # Track visited cells
        current_cell = (math.floor(current_x), math.floor(current_y))
        self.visited_cells.add(current_cell)

        # Check for coverage completion
        if len(self.visited_cells) >= 320 or self.elapsed_time() > 110:
            self.complete('SUCCESS')
            return

        # Stuck detection
        if stuck or (velocity["linear"] < 0.005 and self.state == 'MOVE_TO_WAYPOINT'):
            self.stuck_counter += 1
        else:
            self.stuck_counter = 0

        if self.stuck_counter > 15:
            self.state = 'RECOVER'

        # Obstacle avoidance
        if obstacles["front"] < 0.3:
            self.stop()
            self.state = 'AVOID_OBSTACLE'
            self.avoid_counter = 0
        elif obstacles["front"] < 0.5:
            steer = 0.2 if obstacles["front_left"] < obstacles["front_right"] else -0.2
            self.move(linear=0.2, angular=steer)
            return

        # State machine
        if self.state == 'MOVE_TO_WAYPOINT':
            if self.current_waypoint_index >= len(self.waypoints):
                self.complete('SUCCESS')
                return

            waypoint = self.waypoints[self.current_waypoint_index]
            target_x, target_y = waypoint
            heading_error = self.heading_to(target_x, target_y)
            angular = max(min(heading_error * 0.05, 1.0), -1.0)

            if self.distance_to(target_x, target_y) < 1.0:
                self.current_waypoint_index += 1

            self.move(linear=0.5, angular=angular)

        elif self.state == 'AVOID_OBSTACLE':
            self.avoid_counter += 1
            if self.avoid_counter <= 15:
                self.move(linear=-0.15)
            elif self.avoid_counter <= 30:
                self.move(linear=0.15, angular=0.6)
            else:
                self.state = 'MOVE_TO_WAYPOINT'

        elif self.state == 'RECOVER':
            if self.recover_counter < 20:
                self.move(linear=-0.15)
            elif self.recover_counter < 40:
                self.move(angular=0.3)
            else:
                self.state = 'MOVE_TO_WAYPOINT'
                self.recover_counter = 0
            self.recover_counter += 1