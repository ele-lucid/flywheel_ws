"""Shared fixtures for flywheel tests."""

import json
import os
import sys
import tempfile

import pytest

# Add source packages to path so we can import without ROS/colcon
SRC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src')
sys.path.insert(0, os.path.join(SRC_DIR, 'flywheel_orchestrator'))
sys.path.insert(0, os.path.join(SRC_DIR, 'flywheel_missions'))
sys.path.insert(0, os.path.join(SRC_DIR, 'flywheel_perception'))
sys.path.insert(0, os.path.join(SRC_DIR, 'flywheel_common'))


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory."""
    return str(tmp_path)


@pytest.fixture
def sample_world_state():
    """A realistic world state dict."""
    return {
        "timestamp": 1234567890.0,
        "pose": {"x": 0.0, "y": 0.0, "heading_deg": 0.0},
        "velocity": {"linear": 0.0, "angular": 0.0},
        "obstacles": {
            "front": 5.0, "front_left": 4.0, "left": 3.0, "back_left": 99.0,
            "back": 99.0, "back_right": 99.0, "right": 6.0, "front_right": 4.5,
        },
        "depth": {"closest": 2.0, "mean": 5.0, "obstacle_fraction": 0.1},
        "imu": {"heading_deg": 0.0, "roll_deg": 0.0, "pitch_deg": 0.0, "stuck": False},
        "stuck": False,
        "goals_visited": [],
        "goals_remaining": [
            {"id": 0, "x": 5.0, "y": 5.0},
            {"id": 1, "x": -5.0, "y": -5.0},
            {"id": 2, "x": 7.0, "y": -7.0},
            {"id": 3, "x": -8.0, "y": 7.0},
            {"id": 4, "x": 0.0, "y": -3.0},
        ],
        "goals_total": 5,
    }


@pytest.fixture
def sample_sensor_log(tmp_path):
    """Create a sensor log file with realistic data and return its path."""
    log_path = tmp_path / "sensor_log.jsonl"
    entries = []
    # Simulate robot moving from (0,0) toward goal at (5,5)
    for i in range(100):
        t = i * 0.2  # 5Hz for 20 seconds
        x = i * 0.05  # move ~5m total
        y = i * 0.05
        entry = {
            "timestamp": 1000.0 + t,
            "pose": {"x": round(x, 3), "y": round(y, 3), "heading_deg": 45.0},
            "velocity": {"linear": 0.25, "angular": 0.0},
            "obstacles": {"front": 5.0, "front_left": 5.0, "left": 99.0,
                          "back_left": 99.0, "back": 99.0, "back_right": 99.0,
                          "right": 99.0, "front_right": 5.0},
            "depth": {"closest": 3.0, "mean": 5.0, "obstacle_fraction": 0.05},
            "imu": {"heading_deg": 45.0, "stuck": False},
            "stuck": False,
            "goals_visited": [0] if x > 4.5 and y > 4.5 else [],
            "goals_remaining": [],
        }
        entries.append(entry)

    with open(log_path, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')

    return str(log_path)
