"""Base class for all missions. LLM-generated missions must inherit from this.

Provides:
- /cmd_vel publisher for motion commands
- /perception/world_model subscriber for sensor data
- /mission/status publisher for signaling completion
- Helper methods: move_forward, turn, stop, get_world_state, heading_to, distance_to
- Automatic collision proximity warning
- Timer-based execution loop
"""

import json
import math
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
from nav_msgs.msg import Odometry


class BaseMission(Node):
    """Base class for flywheel missions. Override execute() to define behavior."""

    # Constants available to generated code
    ROBOT_WIDTH = 0.34
    COLLISION_WARN_DIST = 0.3
    COLLISION_STOP_DIST = 0.2

    def __init__(self, node_name='mission_node'):
        super().__init__(node_name)

        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.status_pub = self.create_publisher(String, '/mission/status', 10)

        # Subscribers
        self.world_model_sub = self.create_subscription(
            String, '/perception/world_model', self._world_model_cb, 10)

        # State
        self._world_state = None
        self._world_state_time = 0.0
        self._start_time = time.time()
        self._collision_count = 0
        self._distance_traveled = 0.0
        self._last_pose = None
        self._mission_complete = False
        self._mission_events = []

        # Run execute() at 10Hz via timer
        self._exec_timer = self.create_timer(0.1, self._tick)

        self.get_logger().info(f'Mission {node_name} initialized')
        self._publish_status('STARTED')

    def _world_model_cb(self, msg):
        self._world_state = json.loads(msg.data)
        self._world_state_time = time.time()

        # Track distance
        pose = self._world_state.get('pose', {})
        if self._last_pose is not None:
            dx = pose.get('x', 0) - self._last_pose.get('x', 0)
            dy = pose.get('y', 0) - self._last_pose.get('y', 0)
            self._distance_traveled += math.sqrt(dx*dx + dy*dy)
        self._last_pose = pose

        # Collision proximity check
        obstacles = self._world_state.get('obstacles', {})
        front = obstacles.get('front', 99)
        if front < self.COLLISION_STOP_DIST:
            self._collision_count += 1
            self.stop()
            self.log_event('COLLISION_PROXIMITY', f'Front obstacle at {front}m, emergency stop')

    def _tick(self):
        if self._mission_complete:
            return
        try:
            self.execute()
        except Exception as e:
            self.get_logger().error(f'Mission execute() error: {e}')
            self.log_event('ERROR', str(e))
            self.complete('FAILED')

    # === Methods for generated code to use ===

    def execute(self):
        """Override this method. Called at 10Hz. Use get_world_state() and motion commands."""
        pass

    def get_world_state(self):
        """Returns the latest world model dict, or None if not yet received."""
        if self._world_state is None:
            return None
        # Stale check: if no update in 2 seconds, return None
        if time.time() - self._world_state_time > 2.0:
            return None
        return self._world_state

    def move_forward(self, speed=0.3):
        """Move forward at given speed (m/s). Capped at 0.5 m/s."""
        speed = max(0.0, min(speed, 0.5))
        twist = Twist()
        twist.linear.x = speed
        self.cmd_vel_pub.publish(twist)

    def move(self, linear=0.0, angular=0.0):
        """Move with given linear (m/s) and angular (rad/s) velocities."""
        linear = max(-0.5, min(linear, 0.5))
        angular = max(-1.0, min(angular, 1.0))
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self.cmd_vel_pub.publish(twist)

    def turn(self, angular_vel=0.3):
        """Turn in place. Positive = left, negative = right. Capped at 1.0 rad/s."""
        angular_vel = max(-1.0, min(angular_vel, 1.0))
        twist = Twist()
        twist.angular.z = angular_vel
        self.cmd_vel_pub.publish(twist)

    def stop(self):
        """Stop all motion."""
        self.cmd_vel_pub.publish(Twist())

    def heading_to(self, target_x, target_y):
        """Returns heading error in degrees to target. Positive = turn left."""
        state = self.get_world_state()
        if state is None:
            return 0.0
        pose = state['pose']
        dx = target_x - pose['x']
        dy = target_y - pose['y']
        target_heading = math.degrees(math.atan2(dy, dx))
        error = target_heading - pose['heading_deg']
        # Normalize to -180..180
        while error > 180:
            error -= 360
        while error < -180:
            error += 360
        return error

    def distance_to(self, target_x, target_y):
        """Returns distance in meters to target."""
        state = self.get_world_state()
        if state is None:
            return float('inf')
        pose = state['pose']
        dx = target_x - pose['x']
        dy = target_y - pose['y']
        return math.sqrt(dx*dx + dy*dy)

    def elapsed_time(self):
        """Seconds since mission start."""
        return time.time() - self._start_time

    def log_event(self, event_type, detail=''):
        """Log a mission event."""
        entry = {
            'time': round(self.elapsed_time(), 2),
            'event': event_type,
            'detail': detail,
        }
        self._mission_events.append(entry)
        self.get_logger().info(f'[{event_type}] {detail}')

    def complete(self, status='SUCCESS'):
        """Signal mission completion."""
        if self._mission_complete:
            return
        self._mission_complete = True
        self.stop()
        self._publish_status(status)
        self.log_event('COMPLETE', status)
        self.get_logger().info(f'Mission complete: {status}')

    def get_mission_summary(self):
        """Returns summary dict for evaluation."""
        state = self.get_world_state() or {}
        return {
            'duration': round(self.elapsed_time(), 2),
            'distance_traveled': round(self._distance_traveled, 2),
            'collision_count': self._collision_count,
            'goals_visited': state.get('goals_visited', []),
            'goals_remaining': len(state.get('goals_remaining', [])),
            'events': self._mission_events,
            'completed': self._mission_complete,
        }

    def _publish_status(self, status):
        msg = String()
        msg.data = json.dumps({
            'status': status,
            'time': round(self.elapsed_time(), 2),
            'summary': self.get_mission_summary() if status != 'STARTED' else {},
        })
        self.status_pub.publish(msg)
