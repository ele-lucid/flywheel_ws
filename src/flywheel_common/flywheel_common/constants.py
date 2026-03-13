"""Shared constants for the flywheel project.

Single source of truth for goal positions, robot dimensions, velocity limits,
arena geometry, and mission parameters. All packages import from here.
"""

# Goal positions in the arena (matches SDF)
GOALS = [
    {'id': 0, 'x': 5.0, 'y': 5.0},
    {'id': 1, 'x': -5.0, 'y': -5.0},
    {'id': 2, 'x': 7.0, 'y': -7.0},
    {'id': 3, 'x': -8.0, 'y': 7.0},
    {'id': 4, 'x': 0.0, 'y': -3.0},
]

# Proximity threshold for marking a goal as visited (meters)
GOAL_REACH_DIST = 0.8

# Arena geometry
ARENA_SIZE = 20.0          # arena is 20x20 meters
ARENA_CELLS = 350          # reachable 1m grid cells (out of 400 total)

# Robot dimensions
ROBOT_WIDTH = 0.34         # meters

# Collision thresholds (meters)
COLLISION_WARN_DIST = 0.3
COLLISION_STOP_DIST = 0.2

# Velocity limits
MAX_LINEAR_VEL = 0.5       # m/s
MAX_ANGULAR_VEL = 1.0      # rad/s

# Mission parameters
MISSION_TIMEOUT = 120       # seconds
