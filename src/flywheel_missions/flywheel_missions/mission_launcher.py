"""Generic launcher that dynamically imports and runs a mission module.

Usage: ros2 run flywheel_missions run_mission --ros-args -p module:=mission_v001
"""

import importlib
import sys
import rclpy
from rclpy.node import Node


def main(args=None):
    rclpy.init(args=args)

    # Create a temporary node just to read the parameter
    tmp = Node('_mission_param_reader')
    tmp.declare_parameter('module', 'mission_v001')
    module_name = tmp.get_parameter('module').get_parameter_value().string_value
    tmp.destroy_node()

    # Dynamically import the mission module
    full_module = f'flywheel_missions.generated.{module_name}'
    try:
        mod = importlib.import_module(full_module)
    except ImportError as e:
        print(f'Failed to import mission module {full_module}: {e}', file=sys.stderr)
        rclpy.shutdown()
        sys.exit(1)

    # Find the Mission class (first class that has an 'execute' method)
    mission_cls = None
    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, type) and hasattr(obj, 'execute') and name != 'BaseMission':
            mission_cls = obj
            break

    if mission_cls is None:
        print(f'No mission class found in {full_module}', file=sys.stderr)
        rclpy.shutdown()
        sys.exit(1)

    print(f'Launching mission: {mission_cls.__name__} from {full_module}')
    node = mission_cls()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
