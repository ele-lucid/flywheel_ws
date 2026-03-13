"""Deterministic mission scoring. No LLM involved."""

import json
import math
import os


# Goal positions (must match world_model.py)
GOALS = [
    {'id': 0, 'x': 5.0, 'y': 5.0},
    {'id': 1, 'x': -5.0, 'y': -5.0},
    {'id': 2, 'x': 7.0, 'y': -7.0},
    {'id': 3, 'x': -8.0, 'y': 7.0},
    {'id': 4, 'x': 0.0, 'y': -3.0},
]

# Scoring weights
W_GOALS = 0.40
W_EFFICIENCY = 0.15
W_COLLISIONS = 0.20
W_COVERAGE = 0.15
W_COMPLETION = 0.10


def evaluate_mission(mission_result, sensor_log_path=None):
    """Score a mission on 0-100 scale. Returns evaluation dict."""

    # Parse sensor log for odometry trail
    trail = []
    goals_visited = set()
    collision_count = 0

    if sensor_log_path and os.path.exists(sensor_log_path):
        with open(sensor_log_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    pose = entry.get('pose', {})
                    trail.append((pose.get('x', 0), pose.get('y', 0)))
                    for gid in entry.get('goals_visited', []):
                        goals_visited.add(gid)
                except json.JSONDecodeError:
                    continue

    # Supplement from mission result logs
    if hasattr(mission_result, 'stdout'):
        for line in mission_result.stdout.split('\n'):
            if 'COLLISION_PROXIMITY' in line:
                collision_count += 1
            if 'Goal' in line and 'reached' in line:
                # Try to parse goal id
                for g in GOALS:
                    if f"Goal {g['id']}" in line:
                        goals_visited.add(g['id'])

    # === Score components ===

    # 1. Goals reached (40%)
    goals_score = (len(goals_visited) / len(GOALS)) * 100

    # 2. Distance efficiency (15%)
    total_distance = 0
    for i in range(1, len(trail)):
        dx = trail[i][0] - trail[i-1][0]
        dy = trail[i][1] - trail[i-1][1]
        total_distance += math.sqrt(dx*dx + dy*dy)

    if total_distance > 0 and len(goals_visited) > 0:
        # Compute optimal total distance to visited goals from origin
        optimal = 0
        prev = (0, 0)
        for gid in sorted(goals_visited):
            g = GOALS[gid]
            optimal += math.sqrt((g['x']-prev[0])**2 + (g['y']-prev[1])**2)
            prev = (g['x'], g['y'])
        efficiency_score = min(100, (optimal / max(total_distance, 0.1)) * 100)
    else:
        efficiency_score = 0

    # 3. Collision count (20%)
    collision_score = max(0, 100 - collision_count * 25)

    # 4. Coverage (15%) - unique 1m grid cells visited
    visited_cells = set()
    for x, y in trail:
        visited_cells.add((int(x), int(y)))
    # Arena is 20x20 = 400 cells, but ~350 reachable
    reachable = 350
    coverage_score = min(100, (len(visited_cells) / reachable) * 100)

    # 5. Completion (10%)
    if mission_result.timed_out:
        completion_score = 30  # Partial credit for running full time
    elif mission_result.crashed:
        completion_score = 0
    else:
        completion_score = 100

    # Weighted total
    total = (
        goals_score * W_GOALS +
        efficiency_score * W_EFFICIENCY +
        collision_score * W_COLLISIONS +
        coverage_score * W_COVERAGE +
        completion_score * W_COMPLETION
    )

    evaluation = {
        'total_score': round(total, 1),
        'goals_score': round(goals_score, 1),
        'efficiency_score': round(efficiency_score, 1),
        'collision_score': round(collision_score, 1),
        'coverage_score': round(coverage_score, 1),
        'completion_score': round(completion_score, 1),
        'details': {
            'goals_visited': sorted(goals_visited),
            'goals_total': len(GOALS),
            'total_distance': round(total_distance, 2),
            'collision_count': collision_count,
            'cells_visited': len(visited_cells),
            'duration': round(mission_result.duration, 2),
            'timed_out': mission_result.timed_out,
            'crashed': mission_result.crashed,
        }
    }

    return evaluation
