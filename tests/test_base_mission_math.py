"""Tests for BaseMission math helpers (no ROS dependency).

Tests heading_to, distance_to, and velocity capping by extracting
the pure math logic. These don't instantiate ROS nodes.
"""

import math
import pytest


# Extract the math from BaseMission without importing ROS
def heading_to(pose_x, pose_y, pose_heading_deg, target_x, target_y):
    """Pure math version of BaseMission.heading_to()."""
    dx = target_x - pose_x
    dy = target_y - pose_y
    target_heading = math.degrees(math.atan2(dy, dx))
    error = target_heading - pose_heading_deg
    while error > 180:
        error -= 360
    while error < -180:
        error += 360
    return error


def distance_to(pose_x, pose_y, target_x, target_y):
    """Pure math version of BaseMission.distance_to()."""
    dx = target_x - pose_x
    dy = target_y - pose_y
    return math.sqrt(dx * dx + dy * dy)


def clamp_linear(v):
    return max(-0.5, min(v, 0.5))


def clamp_angular(v):
    return max(-1.0, min(v, 1.0))


class TestHeadingTo:
    def test_target_ahead(self):
        # Robot at origin facing east (0 deg), target at (5, 0)
        error = heading_to(0, 0, 0, 5, 0)
        assert error == pytest.approx(0.0, abs=0.1)

    def test_target_left(self):
        # Robot at origin facing east, target at (0, 5) = 90 degrees
        error = heading_to(0, 0, 0, 0, 5)
        assert error == pytest.approx(90.0, abs=0.1)

    def test_target_right(self):
        # Robot at origin facing east, target at (0, -5) = -90 degrees
        error = heading_to(0, 0, 0, 0, -5)
        assert error == pytest.approx(-90.0, abs=0.1)

    def test_target_behind(self):
        # Robot at origin facing east, target at (-5, 0) = 180 degrees
        error = heading_to(0, 0, 0, -5, 0)
        assert abs(error) == pytest.approx(180.0, abs=0.1)

    def test_wrap_around_positive(self):
        # Robot facing 170 degrees, target at 190 degrees equivalent
        # heading_to(-5, 1) when at origin facing 170 deg
        error = heading_to(0, 0, 170, -5, 1)
        # Target is slightly past 180, so error should be small positive or wrap
        assert -180 <= error <= 180

    def test_wrap_around_negative(self):
        # Robot facing -170 degrees, target behind-left
        error = heading_to(0, 0, -170, -5, -1)
        assert -180 <= error <= 180

    def test_same_position(self):
        # Target at robot position -- atan2(0,0) = 0
        error = heading_to(5, 5, 45, 5, 5)
        # Result is -45 (target heading 0, robot heading 45)
        assert error == pytest.approx(-45.0, abs=0.1)


class TestDistanceTo:
    def test_same_position(self):
        assert distance_to(0, 0, 0, 0) == 0.0

    def test_unit_distance(self):
        assert distance_to(0, 0, 1, 0) == pytest.approx(1.0)
        assert distance_to(0, 0, 0, 1) == pytest.approx(1.0)

    def test_diagonal(self):
        assert distance_to(0, 0, 3, 4) == pytest.approx(5.0)

    def test_negative_coords(self):
        assert distance_to(-3, -4, 0, 0) == pytest.approx(5.0)

    def test_large_distance(self):
        # Goal at (8, 7) from origin
        d = distance_to(0, 0, 8, 7)
        assert d == pytest.approx(math.sqrt(113), abs=0.01)


class TestVelocityClamping:
    def test_linear_normal(self):
        assert clamp_linear(0.3) == 0.3

    def test_linear_max(self):
        assert clamp_linear(1.0) == 0.5

    def test_linear_min(self):
        assert clamp_linear(-1.0) == -0.5

    def test_angular_normal(self):
        assert clamp_angular(0.5) == 0.5

    def test_angular_max(self):
        assert clamp_angular(2.0) == 1.0

    def test_angular_min(self):
        assert clamp_angular(-2.0) == -1.0
