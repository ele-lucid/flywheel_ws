"""Post-mission log analysis via LLM. Extracts lessons and failure modes."""

import json
import os
from .llm_client import LLMClient

ANALYSIS_SYSTEM_PROMPT = """You are a robotics debugging expert. You analyze mission logs from a differential drive robot navigating an arena with obstacles and goals.

Your job: identify what went wrong (or right), extract root causes, and produce actionable lessons for the next iteration.

Respond with ONLY valid JSON in this exact format:
{
  "failure_modes": ["description of each thing that went wrong"],
  "success_factors": ["description of each thing that worked well"],
  "root_causes": ["underlying reason for each failure"],
  "lessons": ["specific, actionable lesson for next code generation"],
  "next_strategy": "one sentence describing recommended approach for next mission"
}
"""


class LogAnalyzer:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def analyze(self, code, evaluation, sensor_log_path=None, mission_stdout='', mission_stderr=''):
        """Analyze a completed mission and return structured insights."""

        prompt_parts = []

        # Evaluation summary
        prompt_parts.append(f"## Evaluation Scores\n```json\n{json.dumps(evaluation, indent=2)}\n```\n")

        # The code that ran
        prompt_parts.append(f"## Mission Code\n```python\n{code}\n```\n")

        # Key log excerpts
        if mission_stderr:
            # Truncate to last 2000 chars
            stderr_excerpt = mission_stderr[-2000:] if len(mission_stderr) > 2000 else mission_stderr
            prompt_parts.append(f"## stderr (errors/warnings)\n```\n{stderr_excerpt}\n```\n")

        if mission_stdout:
            stdout_excerpt = mission_stdout[-2000:] if len(mission_stdout) > 2000 else mission_stdout
            prompt_parts.append(f"## stdout (mission events)\n```\n{stdout_excerpt}\n```\n")

        # Sampled sensor log
        if sensor_log_path and os.path.exists(sensor_log_path):
            samples = []
            with open(sensor_log_path) as f:
                lines = f.readlines()
            # Take every 10th line, max 30 entries
            step = max(1, len(lines) // 30)
            for i in range(0, len(lines), step):
                try:
                    entry = json.loads(lines[i])
                    # Compact version
                    compact = {
                        'pose': entry.get('pose'),
                        'obstacles_front': entry.get('obstacles', {}).get('front', 99),
                        'stuck': entry.get('stuck', False),
                        'goals_visited': entry.get('goals_visited', []),
                    }
                    samples.append(compact)
                except (json.JSONDecodeError, IndexError):
                    pass

            if samples:
                prompt_parts.append(
                    f"## Sensor Log Samples ({len(samples)} of {len(lines)} entries)\n"
                    f"```json\n{json.dumps(samples[:30], indent=1)}\n```\n"
                )

        prompt_parts.append(
            "\n## Task\n"
            "Analyze this mission. Identify failure modes, root causes, and actionable lessons.\n"
            "Be specific: reference actual numbers, positions, and behaviors from the logs.\n"
            "Respond with ONLY the JSON format specified."
        )

        user_prompt = '\n'.join(prompt_parts)

        try:
            analysis = self.llm.chat_json(ANALYSIS_SYSTEM_PROMPT, user_prompt)
        except (json.JSONDecodeError, Exception) as e:
            analysis = {
                'failure_modes': [f'Analysis failed: {e}'],
                'success_factors': [],
                'root_causes': ['Could not parse LLM response'],
                'lessons': ['Ensure mission produces parseable logs'],
                'next_strategy': 'Retry with simpler approach',
            }

        return analysis


class LessonStore:
    """Persistent lesson storage in JSONL format."""

    def __init__(self, filepath):
        self.filepath = filepath
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

    def load(self, max_lessons=50):
        """Load lessons, most recent first."""
        if not os.path.exists(self.filepath):
            return []
        lessons = []
        with open(self.filepath) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        lessons.append(entry.get('lesson', line))
                    except json.JSONDecodeError:
                        lessons.append(line)
        return lessons[-max_lessons:]

    def add(self, lessons, cycle):
        """Append new lessons."""
        with open(self.filepath, 'a') as f:
            for lesson in lessons:
                entry = {'cycle': cycle, 'lesson': lesson}
                f.write(json.dumps(entry) + '\n')

    def clear_recent(self, n=5):
        """Remove the last N lessons (for reset on bad streak)."""
        if not os.path.exists(self.filepath):
            return
        with open(self.filepath) as f:
            lines = f.readlines()
        with open(self.filepath, 'w') as f:
            for line in lines[:-n]:
                f.write(line)


class CodeHistory:
    """Tracks every code version and its score."""

    def __init__(self, filepath):
        self.filepath = filepath
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

    def add(self, cycle, score, code_path):
        with open(self.filepath, 'a') as f:
            entry = {'cycle': cycle, 'score': score, 'code_path': code_path}
            f.write(json.dumps(entry) + '\n')

    def get_best(self):
        """Returns (score, code_path) of best mission, or (0, None)."""
        if not os.path.exists(self.filepath):
            return 0, None
        best_score = 0
        best_path = None
        with open(self.filepath) as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry['score'] > best_score:
                        best_score = entry['score']
                        best_path = entry['code_path']
                except (json.JSONDecodeError, KeyError):
                    pass
        return best_score, best_path
