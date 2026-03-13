#!/usr/bin/env bash
# Installs ROS2 Jazzy, Gazebo Harmonic, and Python deps for the flywheel project.
set -euo pipefail

echo "=== Installing ROS2 Jazzy ==="

# Add ROS2 apt repo
sudo apt-get update && sudo apt-get install -y software-properties-common curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt-get update
sudo apt-get install -y \
    ros-jazzy-desktop \
    ros-jazzy-ros-gz \
    ros-jazzy-ros-gz-bridge \
    ros-jazzy-ros-gz-sim \
    ros-jazzy-robot-state-publisher \
    ros-jazzy-joint-state-publisher \
    ros-jazzy-xacro \
    ros-jazzy-tf2-ros \
    ros-jazzy-rviz2 \
    python3-colcon-common-extensions \
    python3-rosdep

# Init rosdep if not already done
sudo rosdep init 2>/dev/null || true
rosdep update

echo "=== Installing Python deps ==="
pip install --user numpy pyyaml

echo "=== Adding ROS2 to bashrc ==="
if ! grep -q "source /opt/ros/jazzy/setup.bash" ~/.bashrc; then
    echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
fi

echo "=== Done! Source your bashrc or run: source /opt/ros/jazzy/setup.bash ==="
