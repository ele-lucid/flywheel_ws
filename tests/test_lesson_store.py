"""Tests for LessonStore and CodeHistory persistence."""

import json
import os

import pytest

from flywheel_orchestrator.log_analyzer import LessonStore, CodeHistory


class TestLessonStoreLoad:
    def test_load_empty_file(self, tmp_path):
        path = str(tmp_path / "lessons.jsonl")
        open(path, 'w').close()
        store = LessonStore(path)
        assert store.load() == []

    def test_load_missing_file(self, tmp_path):
        path = str(tmp_path / "nonexistent.jsonl")
        store = LessonStore(path)
        assert store.load() == []

    def test_load_returns_lesson_strings(self, tmp_path):
        path = str(tmp_path / "lessons.jsonl")
        with open(path, 'w') as f:
            f.write(json.dumps({"cycle": 1, "lesson": "Turn left when stuck"}) + "\n")
            f.write(json.dumps({"cycle": 2, "lesson": "Slow down near walls"}) + "\n")
        store = LessonStore(path)
        lessons = store.load()
        assert len(lessons) == 2
        assert "Turn left when stuck" in lessons
        assert "Slow down near walls" in lessons

    def test_load_with_max_lessons(self, tmp_path):
        path = str(tmp_path / "lessons.jsonl")
        with open(path, 'w') as f:
            for i in range(20):
                f.write(json.dumps({"cycle": i, "lesson": f"Lesson {i}"}) + "\n")
        store = LessonStore(path)
        lessons = store.load(max_lessons=5)
        assert len(lessons) == 5
        # Should be the most recent 5
        assert lessons[-1] == "Lesson 19"

    def test_load_malformed_jsonl(self, tmp_path):
        path = str(tmp_path / "lessons.jsonl")
        with open(path, 'w') as f:
            f.write('not valid json\n')
            f.write(json.dumps({"cycle": 1, "lesson": "Good lesson"}) + "\n")
            f.write('{"broken\n')
        store = LessonStore(path)
        lessons = store.load()
        # Should skip bad lines and return valid ones
        assert "Good lesson" in lessons


class TestLessonStoreAdd:
    def test_add_creates_file(self, tmp_path):
        path = str(tmp_path / "lessons.jsonl")
        store = LessonStore(path)
        store.add(["First lesson", "Second lesson"], cycle=1)
        assert os.path.exists(path)
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 2
        entry = json.loads(lines[0])
        assert entry["cycle"] == 1
        assert entry["lesson"] == "First lesson"

    def test_add_appends(self, tmp_path):
        path = str(tmp_path / "lessons.jsonl")
        store = LessonStore(path)
        store.add(["Lesson A"], cycle=1)
        store.add(["Lesson B"], cycle=2)
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 2


class TestLessonStoreClearRecent:
    def test_clear_recent(self, tmp_path):
        path = str(tmp_path / "lessons.jsonl")
        store = LessonStore(path)
        for i in range(10):
            store.add([f"Lesson {i}"], cycle=i)
        store.clear_recent(n=3)
        lessons = store.load()
        assert len(lessons) == 7
        assert "Lesson 9" not in lessons

    def test_clear_recent_missing_file(self, tmp_path):
        path = str(tmp_path / "nonexistent.jsonl")
        store = LessonStore(path)
        store.clear_recent(n=5)  # Should not raise

    def test_clear_more_than_exists(self, tmp_path):
        path = str(tmp_path / "lessons.jsonl")
        store = LessonStore(path)
        store.add(["Only one"], cycle=1)
        store.clear_recent(n=10)
        lessons = store.load()
        assert len(lessons) == 0


class TestCodeHistory:
    def test_empty_history(self, tmp_path):
        path = str(tmp_path / "history.jsonl")
        history = CodeHistory(path)
        score, code_path = history.get_best()
        assert score == 0
        assert code_path is None

    def test_add_and_get_best(self, tmp_path):
        path = str(tmp_path / "history.jsonl")
        history = CodeHistory(path)
        history.add(1, 25.0, "/path/to/v1.py")
        history.add(2, 75.0, "/path/to/v2.py")
        history.add(3, 50.0, "/path/to/v3.py")
        score, code_path = history.get_best()
        assert score == 75.0
        assert code_path == "/path/to/v2.py"

    def test_malformed_line_skipped(self, tmp_path):
        path = str(tmp_path / "history.jsonl")
        with open(path, 'w') as f:
            f.write('bad json\n')
            f.write(json.dumps({"cycle": 1, "score": 42, "code_path": "/ok.py"}) + "\n")
        history = CodeHistory(path)
        score, code_path = history.get_best()
        assert score == 42
        assert code_path == "/ok.py"

    def test_missing_file(self, tmp_path):
        path = str(tmp_path / "nope.jsonl")
        history = CodeHistory(path)
        score, _ = history.get_best()
        assert score == 0
