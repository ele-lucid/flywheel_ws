#!/usr/bin/env bash
# Kill all flywheel processes and reset
echo "Killing Gazebo and ROS2 nodes..."
pkill -f "gz sim" 2>/dev/null || true
pkill -f "gzserver" 2>/dev/null || true
pkill -f "flywheel" 2>/dev/null || true
pkill -f "ros2" 2>/dev/null || true
sleep 2
echo "Reset complete."
