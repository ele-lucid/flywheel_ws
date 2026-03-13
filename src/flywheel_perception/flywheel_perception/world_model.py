"""Fuses all sensor summaries + odometry into a unified world model JSON."""

import json
import math
import time
import os
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from nav_msgs.msg import Odometry

# Goal positions in the arena (matches SDF)
GOALS = [
    {'id': 0, 'x': 5.0, 'y': 5.0},
    {'id': 1, 'x': -5.0, 'y': -5.0},
    {'id': 2, 'x': 7.0, 'y': -7.0},
    {'id': 3, 'x': -8.0, 'y': 7.0},
    {'id': 4, 'x': 0.0, 'y': -3.0},
]
GOAL_REACH_DIST = 0.8  # meters


def quaternion_to_yaw(x, y, z, w):
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    return math.degrees(math.atan2(siny_cosp, cosy_cosp))


class WorldModel(Node):
    def __init__(self):
        super().__init__('world_model')

        # Subscribers
        self.lidar_sub = self.create_subscription(String, '/perception/lidar_summary', self.lidar_cb, 10)
        self.depth_sub = self.create_subscription(String, '/perception/depth_summary', self.depth_cb, 10)
        self.imu_sub = self.create_subscription(String, '/perception/imu_summary', self.imu_cb, 10)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_cb, 10)

        # Publisher
        self.pub = self.create_publisher(String, '/perception/world_model', 10)

        # State
        self.lidar_data = {}
        self.depth_data = {}
        self.imu_data = {}
        self.pose = {'x': 0.0, 'y': 0.0, 'heading_deg': 0.0}
        self.velocity = {'linear': 0.0, 'angular': 0.0}
        self.goals_visited = set()

        # Log file path (set by orchestrator via parameter)
        self.declare_parameter('log_dir', '')
        self.log_dir = self.get_parameter('log_dir').get_parameter_value().string_value
        self.log_file = None
        if self.log_dir:
            os.makedirs(self.log_dir, exist_ok=True)
            self.log_file = open(os.path.join(self.log_dir, 'sensor_log.jsonl'), 'a')

        # Publish fused model at 5Hz
        self.timer = self.create_timer(0.2, self.publish_model)
        self.get_logger().info('World model node started')

    def lidar_cb(self, msg):
        self.lidar_data = json.loads(msg.data)

    def depth_cb(self, msg):
        self.depth_data = json.loads(msg.data)

    def imu_cb(self, msg):
        self.imu_data = json.loads(msg.data)

    def odom_cb(self, msg: Odometry):
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
            if dist < GOAL_REACH_DIST:
                if goal['id'] not in self.goals_visited:
                    self.goals_visited.add(goal['id'])
                    self.get_logger().info(f"Goal {goal['id']} reached!")

    def publish_model(self):
        goals_remaining = [g for g in GOALS if g['id'] not in self.goals_visited]

        model = {
            'timestamp': time.time(),
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
