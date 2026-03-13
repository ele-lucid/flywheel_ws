"""Tests for the deterministic mission evaluator."""

import json
import math
import os

import pytest

from flywheel_orchestrator.evaluator import evaluate_mission, GOALS


class FakeMissionResult:
    """Minimal MissionResult stand-in for testing."""
    def __init__(self, exit_code=0, timed_out=False, crashed=False,
                 stdout='', stderr='', duration=60.0):
        self.exit_code = exit_code
        self.timed_out = timed_out
        self.crashed = crashed
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration


class TestNoGoals:
    def test_empty_sensor_log(self, tmp_path):
        log = tmp_path / "sensor_log.jsonl"
        log.write_text("")
        result = FakeMissionResult()
        ev = evaluate_mission(result, str(log))
        assert ev['goals_score'] == 0.0
        assert ev['coverage_score'] == 0.0
        assert ev['completion_score'] == 100  # normal exit = complete

    def test_missing_sensor_log(self):
        result = FakeMissionResult()
        ev = evaluate_mission(result, "/nonexistent/path.jsonl")
        assert ev['goals_score'] == 0.0

    def test_no_sensor_log_path(self):
        result = FakeMissionResult()
        ev = evaluate_mission(result, None)
        assert ev['goals_score'] == 0.0
        assert ev['total_score'] >= 0


class TestGoalScoring:
    def test_all_goals_visited(self, tmp_path):
        log = tmp_path / "sensor_log.jsonl"
        entry = {
            "pose": {"x": 5.0, "y": 5.0},
            "goals_visited": [0, 1, 2, 3, 4],
        }
        log.write_text(json.dumps(entry) + "\n")
        result = FakeMissionResult()
        ev = evaluate_mission(result, str(log))
        assert ev['goals_score'] == 100.0

    def test_partial_goals(self, tmp_path):
        log = tmp_path / "sensor_log.jsonl"
        entry = {"pose": {"x": 5.0, "y": 5.0}, "goals_visited": [0, 4]}
        log.write_text(json.dumps(entry) + "\n")
        result = FakeMissionResult()
        ev = evaluate_mission(result, str(log))
        assert ev['goals_score'] == pytest.approx(40.0)  # 2/5

    def test_goals_from_stdout(self):
        stdout = "some output\nGoal 0 reached!\nGoal 2 reached!\n"
        result = FakeMissionResult(stdout=stdout)
        ev = evaluate_mission(result)
        assert 0 in ev['details']['goals_visited']
        assert 2 in ev['details']['goals_visited']


class TestCollisionScoring:
    def test_no_collisions(self, tmp_path):
        log = tmp_path / "sensor_log.jsonl"
        log.write_text(json.dumps({"pose": {"x": 0, "y": 0}}) + "\n")
        result = FakeMissionResult()
        ev = evaluate_mission(result, str(log))
        assert ev['collision_score'] == 100.0

    def test_collisions_from_stdout(self):
        stdout = "[COLLISION_PROXIMITY] hit\n[COLLISION_PROXIMITY] hit\n"
        result = FakeMissionResult(stdout=stdout)
        ev = evaluate_mission(result)
        assert ev['collision_score'] == 50.0  # 100 - 2*25

    def test_many_collisions_floor_at_zero(self):
        stdout = "\n".join(["[COLLISION_PROXIMITY]"] * 10)
        result = FakeMissionResult(stdout=stdout)
        ev = evaluate_mission(result)
        assert ev['collision_score'] == 0.0


class TestCoverageScoring:
    def test_coverage_from_trail(self, sample_sensor_log):
        result = FakeMissionResult()
        ev = evaluate_mission(result, sample_sensor_log)
        assert ev['coverage_score'] > 0
        assert ev['details']['cells_visited'] > 0

    def test_stationary_robot(self, tmp_path):
        log = tmp_path / "sensor_log.jsonl"
        lines = []
        for _ in range(50):
            lines.append(json.dumps({"pose": {"x": 0.0, "y": 0.0}}))
        log.write_text("\n".join(lines) + "\n")
        result = FakeMissionResult()
        ev = evaluate_mission(result, str(log))
        assert ev['details']['cells_visited'] == 1


class TestCompletionScoring:
    def test_normal_completion(self):
        result = FakeMissionResult(timed_out=False, crashed=False)
        ev = evaluate_mission(result)
        assert ev['completion_score'] == 100

    def test_timeout(self):
        result = FakeMissionResult(timed_out=True)
        ev = evaluate_mission(result)
        assert ev['completion_score'] == 30

    def test_crash(self):
        result = FakeMissionResult(crashed=True)
        ev = evaluate_mission(result)
        assert ev['completion_score'] == 0


class TestTotalScore:
    def test_total_is_weighted_sum(self, tmp_path):
        log = tmp_path / "sensor_log.jsonl"
        log.write_text(json.dumps({"pose": {"x": 0, "y": 0}}) + "\n")
        result = FakeMissionResult()
        ev = evaluate_mission(result, str(log))
        expected = (
            ev['goals_score'] * 0.40 +
            ev['efficiency_score'] * 0.15 +
            ev['collision_score'] * 0.20 +
            ev['coverage_score'] * 0.15 +
            ev['completion_score'] * 0.10
        )
        assert ev['total_score'] == pytest.approx(expected, abs=0.2)

    def test_malformed_jsonl_lines_skipped(self, tmp_path):
        log = tmp_path / "sensor_log.jsonl"
        log.write_text('not json\n{"pose": {"x": 1, "y": 1}}\nalso not json\n')
        result = FakeMissionResult()
        ev = evaluate_mission(result, str(log))
        # Should not crash, should parse the valid line
        assert ev['details']['cells_visited'] >= 1
