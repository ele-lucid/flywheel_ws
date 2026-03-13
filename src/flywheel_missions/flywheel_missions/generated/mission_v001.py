import math
from flywheel_missions.base_mission import BaseMission

class BoustrophedonCoverage(BaseMission):
    def __init__(self):
        super().__init__('boustrophedon_coverage')
        
        self.X_MIN = -9.3
        self.X_MAX = 9.3
        self.Y_MIN = -9.3
        self.Y_MAX = 9.3
        
        self.waypoints = []
        y = self.Y_MIN
        going_east = True
        while y <= self.Y_MAX:
            if going_east:
                self.waypoints.append((self.X_MIN, y))
                self.waypoints.append((self.X_MAX, y))
            else:
                self.waypoints.append((self.X_MAX, y))
                self.waypoints.append((self.X_MIN, y))
            going_east = not going_east
            y += 1.0

        self.state = 'MOWING'
        self.wp_index = 0

        self.visited_cells = set()
        self.SPEED = 0.45
        self.WP_REACH = 0.8

        self.avoid_ticks = 0
        self.avoid_dir = 1

        self.stuck_counter = 0
        self.recover_ticks = 0

        self.get_logger().info(f'Plan: {len(self.waypoints)} waypoints, '
                               f'{len(self.waypoints)//2} rows')

    def execute(self):
        ws = self.get_world_state()
        if ws is None:
            self.stop()
            return

        pose = ws['pose']
        x, y = pose['x'], pose['y']
        self.visited_cells.add((int(round(x)), int(round(y))))

        if self.elapsed_time() > 110:
            self.log_event('TIMEOUT', f'{len(self.visited_cells)} cells')
            self.complete('SUCCESS')
            return

        if self.recover_ticks > 0:
            self.recover_ticks -= 1
            if self.recover_ticks > 10:
                self.move(-0.2, 0.0)
            else:
                self.turn(0.7)
            return

        if self.avoid_ticks == 0 and abs(ws['velocity']['linear']) < 0.03:
            self.stuck_counter += 1
        else:
            self.stuck_counter = 0

        if ws['stuck'] or self.stuck_counter > 20:
            self.log_event('RECOVER', f'Stuck at ({x:.1f}, {y:.1f})')
            self.recover_ticks = 20
            self.stuck_counter = 0
            self.wp_index = min(self.wp_index + 1, len(self.waypoints) - 1)
            return

        if self.wp_index >= len(self.waypoints):
            self.log_event('DONE', f'{len(self.visited_cells)} cells')
            self.complete('SUCCESS')
            return

        target = self.waypoints[self.wp_index]
        reached = self._navigate(target, ws)
        if reached:
            self.wp_index += 1
            if self.wp_index % 2 == 0:
                row_num = self.wp_index // 2
                self.log_event('ROW', f'Row {row_num}, {len(self.visited_cells)} cells')

    def _navigate(self, target, ws):
        pose = ws['pose']
        dx = target[0] - pose['x']
        dy = target[1] - pose['y']
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < self.WP_REACH:
            return True

        obs = ws.get('obstacles', {})
        front = obs.get('front', 99)
        fl = obs.get('front_left', 99)
        fr = obs.get('front_right', 99)

        if self.avoid_ticks > 0:
            self.avoid_ticks -= 1
            self.move(0.15, 0.6 * self.avoid_dir)
            return False

        if front < 0.3:
            self.avoid_dir = 1 if fl > fr else -1
            self.avoid_ticks = 15
            self.move(-0.15, 0.0)
            return False

        if front < 0.6:
            steer = 0.3 if fl > fr else -0.3
            self.move(0.2, steer)
            return False

        target_hdg = math.degrees(math.atan2(dy, dx))
        err = target_hdg - pose['heading_deg']
        while err > 180:
            err -= 360
        while err < -180:
            err += 360

        if abs(err) > 60:
            self.move(0.02, max(-0.8, min(0.8, err * 0.04)))
            return False

        if abs(err) > 20:
            self.move(0.15, max(-0.6, min(0.6, err * 0.03)))
            return False

        angular = max(-0.5, min(0.5, err * 0.03))
        speed = self.SPEED

        left = obs.get('left', 99)
        right = obs.get('right', 99)
        if left < 0.4:
            angular -= 0.1
        if right < 0.4:
            angular += 0.1

        self.move(speed, angular)
        return False