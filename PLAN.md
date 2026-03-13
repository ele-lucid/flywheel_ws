# Flywheel: Self-Improving Robot Learning System - Master Plan

**Version:** 3.1 (Post Eng Review)
**Date:** 2026-03-13
**Author:** Andrew Ashur / Lucid Bots
**Status:** READY FOR IMPLEMENTATION

### Engineering Review Decisions (2026-03-13)
1. **Reset mechanism:** ROS2 service (not topic) for guaranteed delivery
2. **Pose reset:** Subprocess + pose verification loop (retry once if not at origin)
3. **Spin loop:** Lives in orchestrator, MissionRunner stays clean/testable
4. **Goal constants:** Shared constants module (flywheel_common/constants.py)
5. **Fatal errors:** AuthenticationError and RuntimeError propagate through broad catch
6. **Atomic writes:** LessonStore uses write-to-temp-then-rename
7. **Tests expanded:** 9 additional test cases for plan-introduced codepaths (~58 total)

---

## 1. Vision

Flywheel is a self-improving robot learning system. An LLM generates mission code for a simulated differential drive robot, runs it, scores it, analyzes failures, extracts lessons, and feeds them back into the next generation cycle. No human in the loop.

### 12-Month Ideal State

Multi-arena curriculum learning. The system auto-discovers navigation strategies without being told about them. Lessons transfer across arena layouts. A dashboard shows real-time learning curves. Best-performing code deploys to physical hardware with minimal adaptation.

```
  CURRENT STATE                    THIS PLAN                      12-MONTH IDEAL
  Single arena, single robot       Robust kernel, reliable         Multi-arena, multi-robot,
  No tests, no git, broken         learning loop, observable,      curriculum learning,
  cycle reset, fragile LLM,        tested, version-controlled,     sim-to-real transfer,
  no observability                 correct cycle reset,            auto-discovered strategies,
                                   null-safe data flow             live dashboard
```

---

## 2. Current Architecture

```
  ┌─────────────────────────────────────────────────────────────┐
  │                      ORCHESTRATOR                            │
  │                                                              │
  │  ┌───────────┐  ┌────────────┐  ┌────────────┐             │
  │  │ LLM Client│  │ Code Writer│  │Code Validat│             │
  │  │ (OpenAI)  │──│ (Prompts)  │──│ (AST check)│             │
  │  └───────────┘  └────────────┘  └────────────┘             │
  │        │                                                     │
  │  ┌─────▼─────┐  ┌────────────┐  ┌────────────┐             │
  │  │Log Analyze│  │ Evaluator  │  │  Mission   │             │
  │  │ (LLM)     │  │(Determin.) │  │  Runner    │             │
  │  └───────────┘  └────────────┘  │(Subprocess)│             │
  │                                  └────────────┘             │
  │  ┌───────────┐  ┌────────────┐                              │
  │  │LessonStore│  │CodeHistory │                              │
  │  │(JSONL)    │  │(JSONL)     │                              │
  │  └───────────┘  └────────────┘                              │
  └──────┬──────────────────────────────────┬───────────────────┘
         │ subscribes:                      │ publishes (via mission):
         │  /perception/world_model         │  /cmd_vel
         │  /mission/status                 │  /mission/status
         │  /flywheel/reset (new)           │
         │                                  │
  ┌──────▼──────────────────┐  ┌────────────▼───────────────────┐
  │     PERCEPTION          │  │        MISSIONS                 │
  │                         │  │                                 │
  │  lidar_processor ──┐    │  │  BaseMission (stable kernel)   │
  │  depth_processor ──┤    │  │  generated/mission_vNNN.py     │
  │  imu_processor   ──┤    │  │  (LLM-written each cycle)      │
  │                    ▼    │  │                                 │
  │  world_model (fuser)    │  │                                 │
  └──────────┬──────────────┘  └─────────────────────────────────┘
             │
  ┌──────────▼──────────────┐
  │   GAZEBO SIMULATION     │
  │   diffbot (diff drive)  │
  │   flywheel_arena (20x20)│
  │   ros_gz_bridge         │
  └─────────────────────────┘
```

### Learning Loop (One Cycle)

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │                        ONE FLYWHEEL CYCLE                           │
  │                                                                     │
  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
  │  │ RESET    │───▶│ PERCEIVE │───▶│  REASON  │───▶│   ACT    │     │
  │  │          │    │          │    │          │    │          │     │
  │  │- Robot   │    │- Read    │    │- LLM     │    │- LLM gen │     │
  │  │  to (0,0)│    │  world   │    │  plans   │    │  code    │     │
  │  │- Clear   │    │  model   │    │  mission │    │- Validate│     │
  │  │  goals   │    │  JSON    │    │          │    │- Run as  │     │
  │  │- New log │    │          │    │ (can ret │    │  subproc │     │
  │  │  file    │    │ (can ret │    │  None)   │    │  (120s)  │     │
  │  │- Stop vel│    │  None)   │    │          │    │          │     │
  │  └──────────┘    └──────────┘    └──────────┘    └──────────┘     │
  │       │               │               │               │            │
  │       │          ┌────▼────┐     ┌────▼────┐          │            │
  │       │          │None?    │     │None?    │          ▼            │
  │       │          │Skip     │     │Skip     │   ┌──────────┐       │
  │       │          │cycle    │     │cycle    │   │  LEARN   │       │
  │       │          └─────────┘     └─────────┘   │          │       │
  │       │                                         │- Score   │       │
  │       │          ┌──────────┐                   │  (determ)│       │
  │       │          │  STORE   │◀──────────────────│- Analyze │       │
  │       │          │          │                   │  (LLM)   │       │
  │       │          │- Lessons │                   │- Extract │       │
  │       │          │- Code    │                   │  lessons │       │
  │       │          │  history │                   └──────────┘       │
  │       │          │- Best    │                                      │
  │       │          │  mission │                                      │
  │       │          └──────────┘                                      │
  └───────┼────────────────────────────────────────────────────────────┘
          │
          ▼ next cycle
```

### Data Flow: LLM Call (All Four Paths)

```
  orchestrator calls llm.chat()
          │
          ├── HAPPY PATH: response.choices[0].message.content
          │   └── return string to caller
          │
          ├── NIL PATH: response is None or choices is empty
          │   └── return None, caller checks and skips cycle
          │
          ├── EMPTY PATH: content is empty string ""
          │   └── return "", downstream treats as failed generation
          │
          └── ERROR PATH: API timeout / rate limit / network
              ├── Retry 3x with exponential backoff
              ├── Auth error: raise immediately (no retry)
              └── After max retries: return None, caller skips cycle
```

### Null Propagation Through the Cycle

This is the critical data flow to get right. Every LLM call can return None. Every downstream consumer must handle it.

```
  LLM.chat() ──▶ mission_plan (can be None)
       │
       ├── None? ──▶ log "LLM failed to produce plan" + skip cycle
       │
       ▼
  CodeWriter.generate_mission() ──▶ code (can be None/empty)
       │
       ├── None? ──▶ log "LLM failed to generate code" + skip cycle
       │
       ▼
  validate_mission_code() ──▶ ValidationResult
       │
       ├── not ok? ──▶ fix_code() up to 3x, then skip cycle
       │
       ▼
  MissionRunner.run_mission() ──▶ MissionResult (always valid)
       │
       ▼
  evaluate_mission() ──▶ evaluation dict (always valid, may be all zeros)
       │
       ▼
  LogAnalyzer.analyze() ──▶ analysis dict (always valid, fallback on error)
       │
       ▼
  LessonStore.add() ──▶ persisted (no-op if no lessons)
```

**Rule:** Every function that calls the LLM must check the return value for None before proceeding. The orchestrator's `_run_cycle` is the null-safety boundary. If any LLM call returns None, skip the rest of the cycle, log why, and move on.

---

## 3. Showstopper Bugs (Must Fix Before First Real Run)

These bugs make the learning loop fundamentally broken.

### 3.0a Goals Visited State Never Resets Between Cycles (P0)

**File:** `world_model.py:48`

**Problem:** `self.goals_visited` accumulates across the entire session. Cycle 2+ sees goals from cycle 1 as visited. Scores are meaningless.

**Fix:** Add `/flywheel/reset` topic. Orchestrator publishes reset at cycle start. World model clears goals_visited and opens new sensor log.

```python
# world_model.py - add to __init__
self.reset_sub = self.create_subscription(
    String, '/flywheel/reset', self._reset_cb, 10)

def _reset_cb(self, msg):
    self.goals_visited.clear()
    self.get_logger().info('World model reset: goals cleared')
    # Rotate sensor log to new cycle directory
    if self.log_file:
        self.log_file.close()
        self.log_file = None
    try:
        data = json.loads(msg.data)
        log_dir = data.get('log_dir', '')
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            self.log_file = open(os.path.join(log_dir, 'sensor_log.jsonl'), 'w')
    except (json.JSONDecodeError, OSError) as e:
        self.get_logger().error(f'Reset log rotation failed: {e}')
```

### 3.0b Robot Pose Never Resets Between Cycles (P0)

**Problem:** Robot starts each cycle at its previous ending position.

**Fix:** Use Gazebo's set_pose service. Note: the exact service name depends on the Gazebo version (Harmonic vs Fortress). Must verify at runtime.

```python
# orchestrator.py - new method
def _reset_simulation(self, log_dir):
    """Reset robot pose and world model for a clean cycle."""
    # 1. Stop any residual motion
    stop_msg = Twist()
    # Publish stop via a temporary publisher or reuse
    # (mission process is dead at this point, so /cmd_vel is free)

    # 2. Reset robot pose via Gazebo CLI
    # NOTE: Verify service name with `gz service --list` on first run.
    # Harmonic uses /world/<world_name>/set_pose
    # Fortress uses /world/<world_name>/set_pose
    reset_cmd = [
        'gz', 'service', '-s', '/world/default/set_pose',
        '--reqtype', 'gz.msgs.Pose',
        '--reptype', 'gz.msgs.Boolean',
        '--timeout', '5000',
        '--req', 'name: "diffbot" position: {x: 0, y: 0, z: 0.1} orientation: {w: 1}'
    ]
    try:
        result = subprocess.run(reset_cmd, timeout=10, capture_output=True, text=True)
        if result.returncode != 0:
            self.get_logger().warn(f'Gazebo pose reset failed: {result.stderr}')
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        self.get_logger().warn(f'Gazebo pose reset error: {e}')

    # 3. Reset world model state
    reset_msg = String()
    reset_msg.data = json.dumps({'log_dir': log_dir, 'cycle': self.cycle})
    self.reset_pub.publish(reset_msg)

    # 4. Brief pause for physics to settle + new world model to publish
    # Use spin_once instead of sleep to stay responsive
    for _ in range(10):
        rclpy.spin_once(self, timeout_sec=0.2)
```

### 3.0c Sensor Log Path Mismatch (P0)

**Problem:** World model writes sensor_log.jsonl to its launch-time `log_dir` param (likely empty or wrong). Evaluator reads from cycle log_dir.

**Fix:** Solved by 3.0a. The reset message passes the correct log_dir each cycle.

### 3.0d Null Propagation: LLM Returns None After Retry (P0)

**Problem (NEW in v3):** After adding retry/backoff to `llm_client.py`, `chat()` returns `None` on failure instead of crashing. But the orchestrator currently does:
```python
mission_plan = self.llm.chat(system_prompt, reason_prompt, temperature=0.7)
# ... directly uses mission_plan as a string
```
If `mission_plan` is None, it gets passed to `code_writer.generate_mission()` which embeds it in a prompt string, producing `"## Mission Plan\nNone\n"`. The LLM then generates code for a mission called "None."

Same issue with `code_writer.generate_mission()` which calls `self.llm.chat()` and then `self.llm.extract_code(response)`. If chat returns None, extract_code crashes on `None.strip()`.

**Fix:** Add null checks at every LLM call boundary in the orchestrator:

```python
# In _run_cycle, after REASON phase:
mission_plan = self.llm.chat(system_prompt, reason_prompt, temperature=0.7)
if mission_plan is None:
    self.get_logger().error('LLM failed to produce mission plan. Skipping cycle.')
    self.cycle += 1
    return

# In CodeWriter.generate_mission():
response = self.llm.chat(SYSTEM_PROMPT, user_prompt, temperature=0.7)
if response is None:
    return None  # Caller handles

# In CodeWriter.generate_and_validate():
code = self.generate_mission(world_state, mission_plan, best_code, lessons)
if code is None:
    result = ValidationResult()
    result.fail('LLM failed to generate code')
    return '', result

# In CodeWriter.fix_code():
response = self.llm.chat(SYSTEM_PROMPT, prompt, temperature=0.3)
if response is None:
    return code  # Return unfixed code, let validation catch it
```

---

## 4. Critical Gaps (After Showstoppers)

### 4.1 LLM Error Handling (P0) - Part of Phase 0

**File:** `llm_client.py`

Full retry/backoff implementation. See Section 6 for the complete error/rescue map.

```python
import logging
import re
import time as _time
from openai import (
    APITimeoutError, RateLimitError,
    AuthenticationError, APIConnectionError
)

logger = logging.getLogger(__name__)

class LLMClient:
    def chat(self, system_prompt, user_prompt, temperature=0.7, max_tokens=4096):
        self.call_count += 1
        last_error = None

        for attempt in range(4):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if not response.choices:
                    logger.warning("LLM returned empty choices")
                    return None
                usage = response.usage
                if usage:
                    self.total_tokens += usage.total_tokens
                return response.choices[0].message.content

            except AuthenticationError as e:
                logger.error(f"LLM auth failed (not retrying): {e}")
                raise

            except RateLimitError as e:
                wait = min(2 ** attempt * 5, 60)
                logger.warning(f"LLM rate limited (attempt {attempt+1}/4), waiting {wait}s")
                _time.sleep(wait)
                last_error = e

            except (APITimeoutError, APIConnectionError) as e:
                wait = 2 ** attempt
                logger.warning(f"LLM connection error (attempt {attempt+1}/4): {e}, retry in {wait}s")
                _time.sleep(wait)
                last_error = e

            except Exception as e:
                logger.error(f"Unexpected LLM error: {type(e).__name__}: {e}")
                last_error = e
                break  # Don't retry unknown errors

        logger.error(f"LLM failed after retries: {last_error}")
        return None

    def chat_json(self, system_prompt, user_prompt, temperature=0.4, max_tokens=4096):
        text = self.chat(system_prompt, user_prompt, temperature, max_tokens)
        if text is None:
            return {}

        text = text.strip()
        if text.startswith('```'):
            lines = text.split('\n')
            lines = [l for l in lines if not l.strip().startswith('```')]
            text = '\n'.join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # One retry with stricter prompt
            retry_prompt = (
                f"Your previous response was not valid JSON. "
                f"Respond with ONLY valid JSON.\n\n"
                f"Original request:\n{user_prompt}"
            )
            text = self.chat(system_prompt, retry_prompt, temperature=0.2, max_tokens=max_tokens)
            if text is None:
                return {}
            text = text.strip()
            if text.startswith('```'):
                lines = text.split('\n')
                lines = [l for l in lines if not l.strip().startswith('```')]
                text = '\n'.join(lines)
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse failed after retry: {e}")
                return {}

    def extract_code(self, text):
        if text is None:
            return None
        text = text.strip()
        match = re.search(r'```(?:python)?\s*\n(.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text
```

### 4.2 No Version Control (P0)

**Fix:** `git init`, `.gitignore`, initial commit.

```gitignore
# Runtime artifacts
logs/
memory/*.jsonl
memory/best_mission.py
src/flywheel_missions/flywheel_missions/generated/mission_v[0-9]*.py
!src/flywheel_missions/flywheel_missions/generated/mission_v001.py
flywheel.env

# Build artifacts
build/
install/
log/
__pycache__/
*.pyc
*.egg-info/
```

### 4.3 No Tests (P0)

Tests written alongside each fix. Not deferred to a separate phase.

```
  tests/
    test_code_validator.py      12 cases
    test_evaluator.py            8 cases
    test_lesson_store.py         6 cases
    test_code_history.py         4 cases
    test_llm_client.py           8 cases (mocked OpenAI)
    test_base_mission_math.py    5 cases (pure math, no ROS)
    test_null_propagation.py     6 cases (None through each stage)
```

**Total: ~49 test cases.**

### 4.4 Orchestrator Blocks ROS2 Spin During Mission (P1)

**File:** `mission_runner.py` uses `proc.communicate(timeout=120)`, blocking all ROS callbacks for up to 2 minutes.

**Fix:** Polling loop with `spin_once`:

```python
def run_mission_with_spin(self, module_name, log_dir, node):
    """Run mission subprocess while keeping the orchestrator's ROS2 callbacks alive."""
    proc = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE, env=env, preexec_fn=os.setsid)
    start = time.time()
    stdout_chunks = []
    stderr_chunks = []

    while time.time() - start < self.timeout:
        rclpy.spin_once(node, timeout_sec=0.5)

        retcode = proc.poll()
        if retcode is not None:
            break

        # Early exit if mission signaled completion
        if node._mission_status:
            status_data = node._mission_status
            status = status_data.get('status', '')
            if status in ('SUCCESS', 'FAILED', 'TIMEOUT'):
                node.get_logger().info(f'Mission signaled {status}, waiting 2s for cleanup')
                for _ in range(4):
                    rclpy.spin_once(node, timeout_sec=0.5)
                break

    elapsed = time.time() - start

    if proc.poll() is None:
        # Still running, kill it
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=5)

    stdout, stderr = proc.communicate(timeout=5)
    # ... build MissionResult
```

### 4.5 Consecutive Failure Threshold Logic Is Wrong (P1)

**File:** `orchestrator.py:292-303`

**Problem:** Current logic: score < 10 increments `consecutive_failures`, score >= 10 resets to 0. A sequence like [5, 15, 5, 15, 5] never triggers reset because the 15s reset the counter. The system oscillates between bad and mediocre without ever resetting lessons.

**Fix:** Track a rolling window of the last N scores. If the median of the last 5 scores is below 15, trigger a lesson reset. This catches oscillating failure patterns.

```python
# Replace consecutive_failures with a score window
self._recent_scores = []
MAX_RECENT = 5
STAGNATION_THRESHOLD = 15

# After evaluation:
self._recent_scores.append(evaluation['total_score'])
if len(self._recent_scores) > MAX_RECENT:
    self._recent_scores.pop(0)

if len(self._recent_scores) >= MAX_RECENT:
    median = sorted(self._recent_scores)[MAX_RECENT // 2]
    if median < STAGNATION_THRESHOLD:
        self.get_logger().warn(f'Median of last {MAX_RECENT} scores is {median}. Resetting lessons.')
        self.lessons.clear_recent(n=MAX_RECENT * 2)
        self._recent_scores.clear()
```

### 4.6 Evaluator Efficiency Score Is Wrong (P1)

**File:** `evaluator.py:76`

**Fix:** Nearest-neighbor TSP from origin.

```python
def _nearest_neighbor_distance(visited_ids):
    remaining = [GOALS[gid] for gid in visited_ids]
    total = 0.0
    pos = (0.0, 0.0)
    while remaining:
        nearest = min(remaining, key=lambda g: math.hypot(g['x']-pos[0], g['y']-pos[1]))
        total += math.hypot(nearest['x']-pos[0], nearest['y']-pos[1])
        pos = (nearest['x'], nearest['y'])
        remaining.remove(nearest)
    return total
```

### 4.7 Silent Failure: World Model Not Publishing (P1)

**Fix:** Track consecutive None in `wait_for_world_model`. Escalate after thresholds.

```python
# In orchestrator __init__
self._consecutive_no_world = 0

# In _run_cycle, after wait_for_world_model returns None:
if world_state is None:
    self._consecutive_no_world += 1
    if self._consecutive_no_world >= 10:
        self.get_logger().error('No world model for 10 consecutive cycles. Halting.')
        raise RuntimeError('Perception appears dead. Check Gazebo and sensor nodes.')
    elif self._consecutive_no_world >= 5:
        self.get_logger().error(f'No world model for {self._consecutive_no_world} cycles. Check perception.')
    self.cycle += 1
    return

self._consecutive_no_world = 0  # Reset on success
```

### 4.8 Generated Mission Files Accumulate (P2)

**Fix:** After evaluation, delete missions older than the last 5 cycles (except best).

### 4.9 Validator Bypass via getattr (P2)

**Fix:** Add to `BANNED_CALLS` in `code_validator.py`:
```python
BANNED_CALLS = {
    'exec', 'eval', 'compile', '__import__',
    'subprocess', 'os.system', 'os.popen',
    'open',
    'getattr', 'setattr', 'delattr',
    'globals', 'locals', 'vars',
}
```

### 4.10 Lesson Quality Degrades (P2)

**Fix:** Score-weighted storage. Dedup by keyword overlap. Cap at 20 lessons. Details in Phase 2.

### 4.11 No Observability Beyond Log Files (P2)

**Fix:** Terminal dashboard using `rich`. Details in Phase 2.

---

## 5. Implementation Phases

### Phase 0: Unbreak the Loop (2-3 days)

**Goal:** Make the learning loop produce valid, comparable scores.

| # | Task | Files Changed | Test? |
|---|---|---|---|
| 0.1 | `git init` + `.gitignore` + initial commit | new: .gitignore | N/A |
| 0.2 | Add `/flywheel/reset` to world_model | world_model.py, orchestrator.py | Y |
| 0.3 | Robot pose reset via Gazebo service | orchestrator.py | Manual (needs sim) |
| 0.4 | LLM retry/backoff + null returns | llm_client.py | Y (mocked) |
| 0.5 | Regex code extraction | llm_client.py | Y |
| 0.6 | Null propagation guards | orchestrator.py, code_writer.py | Y |
| 0.7 | JSON callback try/except | orchestrator.py | Y |
| 0.8 | pytest setup + test files | new: tests/*.py, conftest.py | N/A |

**Verification:** Run 5 cycles. Confirm each cycle starts at (0,0) with 5 goals remaining. Confirm scores are nonzero. Confirm no crashes on simulated LLM failure.

**Files touched:** 4 modified (orchestrator.py, world_model.py, llm_client.py, code_writer.py), ~8 new (tests + .gitignore)

### Phase 1: Reliable Loop (1 week)

| # | Task | Files Changed | Test? |
|---|---|---|---|
| 1.1 | Spin-aware mission runner | mission_runner.py, orchestrator.py | Y |
| 1.2 | Fix efficiency scorer | evaluator.py | Y |
| 1.3 | Rolling failure detection | orchestrator.py | Y |
| 1.4 | World model health monitoring | orchestrator.py | Y |
| 1.5 | Validator hardening (getattr ban) | code_validator.py | Y |
| 1.6 | Generated file cleanup | mission_runner.py | Y |
| 1.7 | Remaining unit tests | tests/*.py | N/A |

**Verification:** Run 20 cycles. Confirm early mission completion detection works. Confirm stagnation detection triggers lesson reset. Confirm no zombie processes.

### Phase 2: Observe & Improve (2 weeks)

| # | Task | Files Changed |
|---|---|---|
| 2.1 | Terminal dashboard (rich) | new: scripts/dashboard.py |
| 2.2 | LLM cost tracking | llm_client.py, orchestrator.py |
| 2.3 | Lesson dedup + quality scoring | log_analyzer.py |
| 2.4 | Sensor health monitoring | world_model.py |
| 2.5 | Integration test (mocked full cycle) | new: tests/test_integration.py |

### Phase 3: Learning Quality (2 weeks)

| # | Task | Files Changed |
|---|---|---|
| 3.1 | Curriculum (start single-goal, expand) | orchestrator.py, code_writer.py |
| 3.2 | Score plateau detection + temp bump | orchestrator.py |
| 3.3 | Code diff analysis | new: scripts/diff_analysis.py |
| 3.4 | Arena obstacle randomization | flywheel_arena.sdf or launch param |

---

## 6. Error & Rescue Registry (Complete)

```
  METHOD/CODEPATH              | FAILURE MODE              | EXCEPTION               | RESCUED | FIX PHASE | USER SEES
  -----------------------------|---------------------------|-------------------------|---------|-----------|----------
  LLMClient.chat()             | API timeout               | APITimeoutError         | Y       | Ph0       | Retry/None
  LLMClient.chat()             | Rate limit 429            | RateLimitError          | Y       | Ph0       | Backoff/None
  LLMClient.chat()             | Auth failure 401          | AuthenticationError     | Y       | Ph0       | Raise (halt)
  LLMClient.chat()             | Network error             | APIConnectionError      | Y       | Ph0       | Retry/None
  LLMClient.chat()             | Empty choices             | (checked)               | Y       | Ph0       | None
  LLMClient.chat()             | Unexpected error          | Exception               | Y       | Ph0       | None + log
  LLMClient.chat_json()        | JSON parse x2             | JSONDecodeError         | Y       | Ph0       | Empty {}
  LLMClient.extract_code()     | Missing/bad fence         | (regex)                 | Y       | Ph0       | Raw text
  LLMClient.extract_code()     | None input                | (checked)               | Y       | Ph0       | None
  Orchestrator._world_cb()     | Bad JSON                  | JSONDecodeError         | Y       | Ph0       | Skip
  Orchestrator._status_cb()    | Bad JSON                  | JSONDecodeError         | Y       | Ph0       | Skip
  Orchestrator._run_cycle()    | Any unhandled             | Exception               | Y       | Exists    | Log + next
  Orchestrator.REASON          | LLM returns None          | (checked)               | Y       | Ph0       | Skip cycle
  CodeWriter.generate          | LLM returns None          | (checked)               | Y       | Ph0       | Skip cycle
  CodeWriter.fix_code          | LLM returns None          | (checked)               | Y       | Ph0       | Return unfixed
  CodeWriter.gen_and_validate  | Code is None              | (checked)               | Y       | Ph0       | Skip cycle
  MissionRunner.run_mission()  | Subprocess spawn fail     | Exception               | Y       | Exists    | Crashed
  MissionRunner.run_mission()  | Process kill fails        | ProcessLookupError      | Y       | Exists    | OK
  LogAnalyzer.analyze()        | LLM fails                 | Exception               | Y       | Exists    | Fallback
  LessonStore.load()           | Bad JSONL line            | JSONDecodeError         | Y       | Exists    | Skip line
  WorldModel.publish_model()   | Sensors stale/empty       | (no check)              | Y       | Ph1       | Log
  WorldModel._reset_cb()       | Bad JSON / file error     | JSONDecodeError/OSError | Y       | Ph0       | Log
  _reset_simulation()          | gz service fails          | TimeoutExpired/FNF      | Y       | Ph0       | Log + continue
  BaseMission._tick()          | execute() throws          | Exception               | Y       | Exists    | FAILED
  evaluate_mission()           | No sensor log             | (checked)               | Y       | Exists    | Zero scores
```

**After Phase 0: 0 CRITICAL GAPS.**

---

## 7. Failure Modes Registry

```
  CODEPATH                | FAILURE MODE              | RESCUED | TEST | USER SEES     | LOGGED | STATUS
  ------------------------|---------------------------|---------|------|---------------|--------|--------
  LLMClient.chat          | API timeout               | Y (Ph0) | Y    | Retry/None    | Y      | OK
  LLMClient.chat          | Rate limit 429            | Y (Ph0) | Y    | Backoff/None  | Y      | OK
  LLMClient.chat          | Auth failure 401          | Y (Ph0) | Y    | Halt          | Y      | OK
  LLMClient.chat_json     | Double JSON fail          | Y (Ph0) | Y    | Empty dict    | Y      | OK
  LLMClient.extract_code  | Bad fence                 | Y (Ph0) | Y    | Raw text      | Y      | OK
  Orchestrator.REASON     | LLM returns None          | Y (Ph0) | Y    | Skip cycle    | Y      | OK
  CodeWriter.generate     | LLM returns None          | Y (Ph0) | Y    | Skip cycle    | Y      | OK
  Orchestrator._world_cb  | Bad JSON                  | Y (Ph0) | N    | Skip update   | Y      | OK
  WorldModel              | goals not reset           | Y (Ph0) | Y    | Clean reset   | Y      | OK
  WorldModel              | sensors stale             | Y (Ph1) | N    | Log warning   | Y      | OK
  Evaluator               | Wrong efficiency          | Y (Ph1) | Y    | Correct score | N/A    | OK
  MissionRunner           | Zombie process            | Y (Ph1) | N    | Killed        | Y      | OK
  Orchestrator            | No world model x10        | Y (Ph1) | N    | Halt          | Y      | OK
  Orchestrator            | Score stagnation          | Y (Ph1) | Y    | Lesson reset  | Y      | OK
  LessonStore             | Contradicting lessons     | Y (Ph2) | Y    | Deduped       | Y      | OK
```

**0 CRITICAL GAPS. 0 WARNINGS.**

---

## 8. Security

| # | Threat | Likelihood | Impact | Mitigated | Phase |
|---|---|---|---|---|---|
| 1 | getattr(os, 'system') bypass | Med | High | Ban getattr in validator | Ph1 |
| 2 | numpy.load file read | Low | Med | Accept risk | - |
| 3 | API key in git | Med | High | .gitignore | Ph0 |
| 4 | Network calls via ROS libs | Low | Low | Accept risk | - |
| 5 | ROS topic injection | Low | Med | Trusted LAN | - |

---

## 9. Reuse Map

| Sub-problem | Existing Code | Changes |
|---|---|---|
| Sensor fusion | flywheel_perception (4 nodes) | Add reset subscriber |
| Mission API | BaseMission | None |
| Code validation | code_validator.py | Ban getattr/setattr |
| Scoring | evaluator.py | Fix efficiency calc |
| LLM integration | llm_client.py | Retry/backoff, regex extract |
| Lessons | LessonStore | Dedup in Phase 2 |
| Code history | CodeHistory | None |
| Launch script | run_flywheel.sh | None |
| Metrics | export_metrics.py | Extend in Phase 2 |

---

## 10. NOT In Scope

- Multi-robot support
- Physical hardware deployment
- Alternative simulators (Isaac Sim, MuJoCo)
- Web dashboard
- Multi-LLM comparison
- Path planning in generated code
- Arena randomization before Phase 3
- Container isolation for missions

---

## 11. Cost Estimate

**GPT-4o per cycle (typical):** ~15K input tokens, ~2K output tokens = ~$0.06
**GPT-4o per cycle (worst, 20 calls):** ~40K input + 6K output = ~$0.16
**100 cycles typical:** ~$6
**100 cycles worst:** ~$16

Acceptable for development. Monitor with Phase 2 cost tracking.

---

## 12. Operations

### Run
```bash
cd /home/andrew-ashur/projects/flywheel_ws
./scripts/run_flywheel.sh
```

### Monitor
```bash
python3 scripts/export_metrics.py        # Score table
tail -f logs/cycle_*/cycle_summary.json   # Live cycle summaries
# Phase 2: python3 scripts/dashboard.py
```

### Reset
```bash
rm -rf logs/ memory/lessons.jsonl memory/code_history.jsonl
```

### Rollback
`git revert <commit>` (after Phase 0 git init)

---

## 13. Verification Checklist

After Phase 0, manually verify:
- [ ] `git log` shows initial commit
- [ ] Run 3 cycles, each starts at (0,0) with 5 remaining goals
- [ ] `sensor_log.jsonl` appears in `logs/cycle_001/`
- [ ] Scores are nonzero (at least coverage + completion scores)
- [ ] Simulate LLM failure (bad API key), confirm graceful skip

After Phase 1:
- [ ] Run 20 cycles, no crashes
- [ ] Mission that calls `complete('SUCCESS')` exits early (not at 120s)
- [ ] `pytest tests/` passes all ~49 tests
- [ ] `getattr(os, 'system')` in test code is rejected by validator

---

## 14. Dream State Delta

**After this plan ships:**
- Reliable: zero silent crashes, null-safe data flow, clean resets
- Trustworthy: ~49 tests, correct scoring, validated code execution
- Observable: terminal dashboard, cost tracking (Phase 2)
- Learning effectively: deduped lessons, stagnation detection, curriculum (Phase 3)

**Still missing vs. 12-month ideal:**
- Multi-arena support
- Sim-to-real transfer
- Strategy taxonomy
- Hardware deployment
- Cross-arena lesson transfer
