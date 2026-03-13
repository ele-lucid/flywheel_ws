"""Processes depth camera image into front obstacle summary."""

import json
import struct
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from rcl_interfaces.msg import ParameterDescriptor
from sensor_msgs.msg import Image
from std_msgs.msg import String

SENSOR_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    durability=DurabilityPolicy.VOLATILE,
)

PROCESSED_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
    durability=DurabilityPolicy.VOLATILE,
)


class DepthProcessor(Node):
    def __init__(self):
        super().__init__('depth_processor')

        self.declare_parameter(
            'obstacle_threshold', 1.0,
            ParameterDescriptor(description='Distance in meters below which a pixel counts as an obstacle'),
        )
        self.obstacle_threshold = self.get_parameter('obstacle_threshold').value

        self.sub = self.create_subscription(Image, '/depth_camera/image_raw', self.depth_cb, SENSOR_QOS)
        self.pub = self.create_publisher(String, '/perception/depth_summary', PROCESSED_QOS)
        self.get_logger().info('Depth processor started (explicit QoS)')

    def depth_cb(self, msg: Image):
        # Convert raw bytes to numpy array
        if msg.encoding == '32FC1':
            depth = np.frombuffer(msg.data, dtype=np.float32).reshape(msg.height, msg.width)
        elif msg.encoding == '16UC1':
            depth = np.frombuffer(msg.data, dtype=np.uint16).reshape(msg.height, msg.width).astype(np.float32) / 1000.0
        else:
            self.get_logger().warn(f'Unknown depth encoding: {msg.encoding}')
            return

        # Filter invalid values
        valid = depth[np.isfinite(depth) & (depth > 0.1) & (depth < 10.0)]

        if len(valid) == 0:
            summary = {'closest': 99.0, 'mean': 99.0, 'obstacle_fraction': 0.0}
        else:
            # What fraction of the image has something closer than the threshold
            close_mask = valid < self.obstacle_threshold
            summary = {
                'closest': round(float(np.min(valid)), 3),
                'mean': round(float(np.mean(valid)), 3),
                'obstacle_fraction': round(float(np.sum(close_mask)) / len(valid), 3),
            }

        out = String()
        out.data = json.dumps(summary)
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = DepthProcessor()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
