"""Tests for shared constants module."""

from flywheel_common.constants import (
    GOALS, GOAL_REACH_DIST, ARENA_SIZE, ARENA_CELLS,
    ROBOT_WIDTH, COLLISION_WARN_DIST, COLLISION_STOP_DIST,
    MAX_LINEAR_VEL, MAX_ANGULAR_VEL, MISSION_TIMEOUT,
)


class TestGoals:
    def test_five_goals(self):
        assert len(GOALS) == 5

    def test_goal_structure(self):
        for goal in GOALS:
            assert 'id' in goal
            assert 'x' in goal
            assert 'y' in goal
            assert isinstance(goal['id'], int)
            assert isinstance(goal['x'], float)
            assert isinstance(goal['y'], float)

    def test_unique_ids(self):
        ids = [g['id'] for g in GOALS]
        assert len(set(ids)) == len(ids)

    def test_goals_within_arena(self):
        half = ARENA_SIZE / 2
        for goal in GOALS:
            assert -half <= goal['x'] <= half
            assert -half <= goal['y'] <= half


class TestLimits:
    def test_velocity_limits_positive(self):
        assert MAX_LINEAR_VEL > 0
        assert MAX_ANGULAR_VEL > 0

    def test_collision_thresholds_ordered(self):
        assert COLLISION_STOP_DIST < COLLISION_WARN_DIST

    def test_goal_reach_dist_positive(self):
        assert GOAL_REACH_DIST > 0

    def test_mission_timeout_positive(self):
        assert MISSION_TIMEOUT > 0

    def test_arena_cells_less_than_total(self):
        total = ARENA_SIZE * ARENA_SIZE
        assert ARENA_CELLS <= total
