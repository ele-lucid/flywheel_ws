#!/usr/bin/env bash
# Launch the full flywheel: Gazebo sim + perception + orchestrator
set -euo pipefail

WS_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WS_DIR"

# Source ROS2
source /opt/ros/jazzy/setup.bash

# Build workspace (first time or after changes)
if [ ! -d "install" ] || [ "${1:-}" = "--build" ]; then
    echo "Building workspace..."
    colcon build --symlink-install
fi

# Source workspace
source install/setup.bash

echo "=== Starting Flywheel ==="
echo "Workspace: $WS_DIR"
echo ""

# Trap to clean up all background processes
cleanup() {
    echo "Shutting down..."
    kill 0 2>/dev/null
    wait 2>/dev/null
    echo "Done."
}
trap cleanup EXIT INT TERM

# 1. Launch Gazebo + robot
echo "[1/3] Launching Gazebo simulation..."
ros2 launch flywheel_description sim.launch.py &
SIM_PID=$!
sleep 10  # Wait for Gazebo to initialize

# 2. Launch perception pipeline
echo "[2/3] Launching perception pipeline..."
ros2 launch flywheel_perception perception.launch.py &
PERC_PID=$!
sleep 3

# 3. Launch orchestrator
echo "[3/3] Launching flywheel orchestrator..."
ros2 run flywheel_orchestrator orchestrator --ros-args -p workspace:="$WS_DIR"

wait
