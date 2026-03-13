"""Processes /scan into 8-sector obstacle distances."""

import math
import json
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String


SECTORS = ['front', 'front_left', 'left', 'back_left', 'back', 'back_right', 'right', 'front_right']
# Each sector covers 45 degrees (pi/4 radians)
# front = -22.5 to 22.5 degrees, front_left = 22.5 to 67.5, etc.
SECTOR_RANGES_DEG = [
    (-22.5, 22.5),    # front
    (22.5, 67.5),     # front_left
    (67.5, 112.5),    # left
    (112.5, 157.5),   # back_left
    (157.5, 202.5),   # back (wraps around)
    (202.5, 247.5),   # back_right
    (247.5, 292.5),   # right
    (292.5, 337.5),   # front_right
]


class LidarProcessor(Node):
    def __init__(self):
        super().__init__('lidar_processor')
        self.sub = self.create_subscription(LaserScan, '/scan', self.scan_cb, 10)
        self.pub = self.create_publisher(String, '/perception/lidar_summary', 10)
        self.get_logger().info('Lidar processor started')

    def scan_cb(self, msg: LaserScan):
        n = len(msg.ranges)
        if n == 0:
            return

        sector_mins = {}
        for i, (lo_deg, hi_deg) in enumerate(SECTOR_RANGES_DEG):
            lo_rad = math.radians(lo_deg)
            hi_rad = math.radians(hi_deg)

            min_dist = float('inf')
            for j in range(n):
                angle = msg.angle_min + j * msg.angle_increment
                # Normalize angle to 0..2pi
                angle_deg = math.degrees(angle) % 360
                if lo_deg < 0:
                    # Handle front sector wrapping
                    if angle_deg >= (360 + lo_deg) or angle_deg <= hi_deg:
                        r = msg.ranges[j]
                        if msg.range_min <= r <= msg.range_max and r < min_dist:
                            min_dist = r
                elif hi_deg > 360:
                    if angle_deg >= lo_deg or angle_deg <= (hi_deg - 360):
                        r = msg.ranges[j]
                        if msg.range_min <= r <= msg.range_max and r < min_dist:
                            min_dist = r
                else:
                    if lo_deg <= angle_deg <= hi_deg:
                        r = msg.ranges[j]
                        if msg.range_min <= r <= msg.range_max and r < min_dist:
                            min_dist = r

            sector_mins[SECTORS[i]] = round(min_dist, 3) if min_dist != float('inf') else 99.0

        out = String()
        out.data = json.dumps(sector_mins)
        self.pub.publish(out)


def main(args=None):
    rclpy.init(args=args)
    node = LidarProcessor()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
