"""Launch all perception nodes."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    log_dir_arg = DeclareLaunchArgument('log_dir', default_value='')

    return LaunchDescription([
        log_dir_arg,

        Node(
            package='flywheel_perception',
            executable='lidar_processor',
            name='lidar_processor',
            output='screen',
        ),
        Node(
            package='flywheel_perception',
            executable='depth_processor',
            name='depth_processor',
            output='screen',
        ),
        Node(
            package='flywheel_perception',
            executable='imu_processor',
            name='imu_processor',
            output='screen',
        ),
        Node(
            package='flywheel_perception',
            executable='world_model',
            name='world_model',
            output='screen',
            parameters=[{'log_dir': LaunchConfiguration('log_dir')}],
        ),
    ])
