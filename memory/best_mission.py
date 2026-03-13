import math
from flywheel_missions.base_mission import BaseMission

class CoverageMission(BaseMission):
    def __init__(self):
        super().__init__()
        self.visited_cells = set()
        self.current_target_index = 0
        self.stuck_counter = 0
        self.recovery_mode = False
        self.backup_ticks = 0
        self.recovery_turn_ticks = 0
        self.row_direction = 1  # 1 for east, -1 for west
        self.waypoints = self.generate_waypoints()
    
    def generate_waypoints(self):
        waypoints = []
        for y in range(-9, 10):
            x_start = -9.3 if self.row_direction == 1 else 9.3
            x_end = 9.3 if self.row_direction == 1 else -9.3
            waypoints.append((x_start, y))
            waypoints.append((x_end, y))
            self.row_direction *= -1
        return waypoints
    
    def execute(self):
        world_state = self.get_world_state()
        if world_state is None:
            return
        
        pose = world_state["pose"]
        obstacles = world_state["obstacles"]
        velocity = world_state["velocity"]
        
        # Check for stuck condition
        if (velocity["linear"] < 0.01 and abs(velocity["angular"]) < 0.01 and
            self.stuck_counter >= 20) or world_state["stuck"]:
            self.recovery_mode = True
            self.stuck_counter = 0

        if self.recovery_mode:
            self.recover_from_stuck()
            return
        
        # Update visited cells
        current_cell = (int(pose["x"]), int(pose["y"]))
        self.visited_cells.add(current_cell)
        
        if self.current_target_index >= len(self.waypoints):
            self.complete(status='SUCCESS')
            return
        
        target_x, target_y = self.waypoints[self.current_target_index]
        heading_error = self.heading_to(target_x, target_y)
        distance_to_target = self.distance_to(target_x, target_y)
        
        # Obstacle avoidance logic
        if obstacles["front"] < 0.3:
            self.stop()
            self.recovery_mode = True
            self.backup_ticks = 15
            return
        elif obstacles["front"] < 0.6:
            steer_direction = -0.5 if obstacles["front_left"] < obstacles["front_right"] else 0.5
            self.move(linear=0.2, angular=steer_direction)
            return
        elif obstacles["left"] < 0.4:
            self.move(linear=0.3, angular=0.3)
            return
        elif obstacles["right"] < 0.4:
            self.move(linear=0.3, angular=-0.3)
            return
        
        # Move towards the next waypoint
        if distance_to_target < 0.5:
            self.current_target_index += 1
        else:
            angular = max(min(heading_error * 0.03, 0.5), -0.5)
            self.move(linear=0.5, angular=angular)
        
        # Increment stuck counter if moving forward
        if velocity["linear"] > 0:
            self.stuck_counter += 1
        else:
            self.stuck_counter = 0

    def recover_from_stuck(self):
        if self.backup_ticks > 0:
            self.move(linear=-0.15)
            self.backup_ticks -= 1
            return
        if self.recovery_turn_ticks < 15:
            self.move(angular=0.6)
            self.recovery_turn_ticks += 1
            return
        # Reset recovery mode
        self.recovery_mode = False
        self.recovery_turn_ticks = 0