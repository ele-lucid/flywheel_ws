"""Launch Gazebo sim with the flywheel robot and ros_gz_bridge."""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_description = get_package_share_directory('flywheel_description')

    urdf_file = os.path.join(pkg_description, 'urdf', 'diffbot.urdf.xacro')
    world_file = os.path.join(pkg_description, 'worlds', 'flywheel_arena.sdf')
    bridge_config = os.path.join(pkg_description, 'config', 'gazebo_bridge.yaml')

    # Process xacro
    robot_description_content = os.popen(f'xacro {urdf_file}').read()

    return LaunchDescription([
        # Gazebo Sim
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('ros_gz_sim'),
                    'launch',
                    'gz_sim.launch.py'
                ])
            ]),
            launch_arguments={
                'gz_args': f'-r {world_file}',
            }.items(),
        ),

        # Spawn robot
        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                '-name', 'flywheel_bot',
                '-topic', 'robot_description',
                '-x', '0', '-y', '0', '-z', '0.1',
            ],
            output='screen',
        ),

        # Robot state publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description_content}],
            output='screen',
        ),

        # ros_gz_bridge
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=['--ros-args', '-p', f'config_file:={bridge_config}'],
            output='screen',
        ),
    ])
