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
        self.waypoints = self.build_waypoints()

    def build_waypoints(self):
        wps = []
        goals = [(5, 5), (-5, -5), (7, -7), (-8, 7), (0, -3)]
        for row, y in enumerate(range(-9, 10)):
            # Insert nearby goal before this row
            for gx, gy in goals:
                if abs(gy - y) < 3.0:
                    wps.append((gx, gy))
            # Row endpoints only
            if row % 2 == 0:
                wps.append((-9.0, float(y)))
                wps.append((9.0, float(y)))
            else:
                wps.append((9.0, float(y)))
                wps.append((-9.0, float(y)))
        # Perimeter sweep
        wps.extend([(9, 9), (-9, 9), (-9, -9), (9, -9)])
        return wps

    def execute(self):
        world_state = self.get_world_state()
        if world_state is None:
            return

        pose = world_state["pose"]
        current_x, current_y = pose["x"], pose["y"]
        velocity = world_state["velocity"]
        obstacles = world_state["obstacles"]
        stuck = world_state["stuck"]
        goals_visited = world_state["goals_visited"]

        current_cell = (math.floor(current_x), math.floor(current_y))
        self.visited_cells.add(current_cell)

        if len(goals_visited) == 5 or self.elapsed_time() > 290:
            self.complete('SUCCESS')
            return

        for goal in world_state["goals_remaining"]:
            if self.distance_to(goal["x"], goal["y"]) < 1.5:
                goals_visited.append(goal["id"])

        if stuck or (velocity["linear"] < 0.1 and self.state == 'MOVE_TO_WAYPOINT'):
            self.stuck_counter += 1
        else:
            self.stuck_counter = 0

        if self.stuck_counter > 10:
            self.state = 'RECOVER'

        if obstacles["front"] < 0.3:
            self.state = 'AVOID_OBSTACLE'
            self.avoid_counter = 0
        elif obstacles["front"] < 0.5:
            steer = 0.8 if obstacles["front_left"] < obstacles["front_right"] else -0.8
            self.move(linear=0.3, angular=steer)
            return

        if self.state == 'MOVE_TO_WAYPOINT':
            if self.current_waypoint_index >= len(self.waypoints):
                self.complete('SUCCESS')
                return

            waypoint = self.waypoints[self.current_waypoint_index]
            target_x, target_y = waypoint
            heading_error = self.heading_to(target_x, target_y)
            angular = max(min(heading_error * 0.05, 1.0), -1.0)

            if self.distance_to(target_x, target_y) < 0.5:
                self.current_waypoint_index += 1

            self.move(linear=0.5, angular=angular)

        elif self.state == 'AVOID_OBSTACLE':
            self.avoid_counter += 1
            if self.avoid_counter <= 10:
                self.move(linear=-0.15)
            elif self.avoid_counter <= 25:
                self.move(linear=0.15, angular=0.8)
            else:
                self.state = 'MOVE_TO_WAYPOINT'

        elif self.state == 'RECOVER':
            if self.recover_counter < 10:
                self.move(linear=-0.3)
            elif self.recover_counter < 25:
                self.move(angular=1.5)
            else:
                self.state = 'MOVE_TO_WAYPOINT'
                self.recover_counter = 0
                self.current_waypoint_index += 1
            self.recover_counter += 1