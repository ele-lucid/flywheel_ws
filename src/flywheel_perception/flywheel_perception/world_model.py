"""Fuses all sensor summaries + odometry into a unified world model JSON."""

import json
import math
import time
import os
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from rcl_interfaces.msg import ParameterDescriptor
from std_msgs.msg import String
from nav_msgs.msg import Odometry
from flywheel_common.constants import GOALS, GOAL_REACH_DIST


def quaternion_to_yaw(x, y, z, w):
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    return math.degrees(math.atan2(siny_cosp, cosy_cosp))


class WorldModel(Node):
    def __init__(self):
        super().__init__('world_model')

        # ── Declare parameters with descriptors ──────────────────────
        self.declare_parameter(
            'log_dir', '',
            ParameterDescriptor(description='Directory for sensor log files'))
        self.declare_parameter(
            'publish_rate', 5.0,
            ParameterDescriptor(description='World model publish rate in Hz'))
        self.declare_parameter(
            'staleness_threshold', 2.0,
            ParameterDescriptor(description='Seconds before sensor data is flagged stale'))
        self.declare_parameter(
            'goal_reach_dist', GOAL_REACH_DIST,
            ParameterDescriptor(description='Distance in meters to consider a goal reached'))

        self.log_dir = self.get_parameter('log_dir').get_parameter_value().string_value
        publish_rate = self.get_parameter('publish_rate').get_parameter_value().double_value
        self.staleness_threshold = self.get_parameter('staleness_threshold').get_parameter_value().double_value
        self.goal_reach_dist = self.get_parameter('goal_reach_dist').get_parameter_value().double_value

        # ── QoS profiles ─────────────────────────────────────────────
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            durability=DurabilityPolicy.VOLATILE,
        )
        odom_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        pub_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            durability=DurabilityPolicy.VOLATILE,
        )
        reset_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        # ── Subscribers ──────────────────────────────────────────────
        self.lidar_sub = self.create_subscription(
            String, '/perception/lidar_summary', self.lidar_cb, sensor_qos)
        self.depth_sub = self.create_subscription(
            String, '/perception/depth_summary', self.depth_cb, sensor_qos)
        self.imu_sub = self.create_subscription(
            String, '/perception/imu_summary', self.imu_cb, sensor_qos)
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_cb, odom_qos)
        self.reset_sub = self.create_subscription(
            String, '/flywheel/reset', self.reset_cb, reset_qos)

        # ── Publisher ────────────────────────────────────────────────
        self.pub = self.create_publisher(String, '/perception/world_model', pub_qos)

        # ── State ────────────────────────────────────────────────────
        self.lidar_data = {}
        self.depth_data = {}
        self.imu_data = {}
        self.pose = {'x': 0.0, 'y': 0.0, 'heading_deg': 0.0}
        self.velocity = {'linear': 0.0, 'angular': 0.0}
        self.goals_visited = set()

        # Sensor staleness tracking
        self.last_update = {
            'lidar': 0.0,
            'depth': 0.0,
            'imu': 0.0,
            'odom': 0.0,
        }

        # ── Log file ────────────────────────────────────────────────
        self.log_file = None
        if self.log_dir:
            os.makedirs(self.log_dir, exist_ok=True)
            self.log_file = open(os.path.join(self.log_dir, 'sensor_log.jsonl'), 'a')

        # Publish fused model at configured rate
        period = 1.0 / publish_rate if publish_rate > 0 else 0.2
        self.timer = self.create_timer(period, self.publish_model)
        self.get_logger().info('World model node started')

    # ── Sensor callbacks ─────────────────────────────────────────────

    def lidar_cb(self, msg):
        self.lidar_data = json.loads(msg.data)
        self.last_update['lidar'] = time.time()

    def depth_cb(self, msg):
        self.depth_data = json.loads(msg.data)
        self.last_update['depth'] = time.time()

    def imu_cb(self, msg):
        self.imu_data = json.loads(msg.data)
        self.last_update['imu'] = time.time()

    def odom_cb(self, msg: Odometry):
        self.last_update['odom'] = time.time()
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        self.pose = {
            'x': round(p.x, 3),
            'y': round(p.y, 3),
            'heading_deg': round(quaternion_to_yaw(q.x, q.y, q.z, q.w), 2),
        }
        self.velocity = {
            'linear': round(msg.twist.twist.linear.x, 3),
            'angular': round(msg.twist.twist.angular.z, 3),
        }

        # Check goal proximity
        for goal in GOALS:
            dist = math.sqrt((p.x - goal['x'])**2 + (p.y - goal['y'])**2)
            if dist < self.goal_reach_dist:
                if goal['id'] not in self.goals_visited:
                    self.goals_visited.add(goal['id'])
                    self.get_logger().info(f"Goal {goal['id']} reached!")

    # ── Reset callback ───────────────────────────────────────────────

    def reset_cb(self, msg):
        self.get_logger().info(f'Reset received: {msg.data}')
        self.goals_visited.clear()
        self.lidar_data = {}
        self.depth_data = {}
        self.imu_data = {}
        self.pose = {'x': 0.0, 'y': 0.0, 'heading_deg': 0.0}
        self.velocity = {'linear': 0.0, 'angular': 0.0}
        self.last_update = {k: 0.0 for k in self.last_update}

        # Rotate log file
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        if self.log_dir:
            self.log_file = open(os.path.join(self.log_dir, 'sensor_log.jsonl'), 'a')

        self.get_logger().info('World model state reset')

    # ── Publisher ────────────────────────────────────────────────────

    def publish_model(self):
        now = time.time()
        goals_remaining = [g for g in GOALS if g['id'] not in self.goals_visited]

        # Check sensor staleness
        stale_sensors = {}
        for sensor, last_t in self.last_update.items():
            if last_t > 0.0 and (now - last_t) > self.staleness_threshold:
                stale_sensors[sensor] = True
                self.get_logger().warn(
                    f'Sensor "{sensor}" data is stale '
                    f'({now - last_t:.1f}s since last update)')

        model = {
            'timestamp': now,
            'pose': self.pose,
            'velocity': self.velocity,
            'obstacles': self.lidar_data,
            'depth': self.depth_data,
            'imu': self.imu_data,
            'stuck': self.imu_data.get('stuck', False),
            'goals_visited': sorted(self.goals_visited),
            'goals_remaining': [{'id': g['id'], 'x': g['x'], 'y': g['y']} for g in goals_remaining],
            'goals_total': len(GOALS),
        }

        if stale_sensors:
            model['stale_sensors'] = stale_sensors

        out = String()
        out.data = json.dumps(model)
        self.pub.publish(out)

        # Log to file
        if self.log_file:
            self.log_file.write(json.dumps(model) + '\n')
            self.log_file.flush()

    def destroy_node(self):
        if self.log_file:
            self.log_file.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = WorldModel()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
