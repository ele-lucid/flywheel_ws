"""Processes IMU data into orientation summary and stuck detection."""

import json
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import String


def quaternion_to_euler(x, y, z, w):
    """Convert quaternion to roll, pitch, yaw in degrees."""
    # Roll
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch
    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi / 2, sinp)
    else:
        pitch = math.asin(sinp)

    # Yaw
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return math.degrees(roll), math.degrees(pitch), math.degrees(yaw)


class ImuProcessor(Node):
    def __init__(self):
        super().__init__('imu_processor')
        self.sub = self.create_subscription(Imu, '/imu', self.imu_cb, 10)
        self.pub = self.create_publisher(String, '/perception/imu_summary', 10)

        # Stuck detection: track angular velocity history
        self.velocity_history = []
        self.max_history = 50  # ~0.5 seconds at 100Hz

        self.get_logger().info('IMU processor started')

    def imu_cb(self, msg: Imu):
        q = msg.orientation
        roll, pitch, yaw = quaternion_to_euler(q.x, q.y, q.z, q.w)

        # Track motion for stuck detection
        lin_accel_mag = math.sqrt(
            msg.linear_acceleration.x ** 2 +
            msg.linear_acceleration.y ** 2
        )
        ang_vel_mag = abs(msg.angular_velocity.z)

        self.velocity_history.append(lin_accel_mag + ang_vel_mag)
        if len(self.velocity_history) > self.max_history:
            self.velocity_history.pop(0)

        # Stuck if average motion is very low for the full window
        avg_motion = sum(self.velocity_history) / len(self.velocity_history) if self.velocity_history else 0
        stuck = len(self.velocity_history) >= self.max_history and avg_motion < 0.05

        summary = {
            'heading_deg': round(yaw, 2),
            'roll_deg': round(roll, 2),
            'pitch_deg': round(pitch, 2),
            'angular_vel_z': round(msg.angular_velocity.z, 4),
            'stuck': stuck,
        }

        out = String()
        out.data = json.dumps(summary)
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = ImuProcessor()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
