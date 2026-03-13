# Flywheel TODOs

## Phase 2-3 Deferred Work

### Native Gazebo pose reset via ROS2 service
**What:** Replace `gz service` subprocess call with a proper ROS2 service client via ros_gz_bridge.
**Why:** Removes CLI dependency, faster execution, no PATH issues. When arena randomization lands in Phase 3, this will need to reset obstacle positions too, making native integration more valuable.
**Pros:** Cleaner, faster, testable.
**Cons:** Requires bridge config research for specific Gazebo Harmonic service API.
**Context:** Currently using subprocess + pose verification as a pragmatic first pass (eng review decision 2A, 2026-03-13). Works fine for single-arena, single-robot. Becomes inadequate when Phase 3 needs obstacle randomization.
**Depends on:** Phase 0 shipping, knowing exact Gazebo Harmonic service API.
**Effort:** M (half day)
**Priority:** P2

### Structured logging (JSON format)
**What:** Replace ROS2 get_logger() calls with structured Python logging so logs are machine-parseable.
**Why:** Currently all orchestrator logs are unstructured prose. Debugging cycle 47's failure means grepping through human-readable strings. Structured logs enable filtering by cycle, phase, severity.
**Pros:** Enables log aggregation, dashboard consumption, better debugging.
**Cons:** ~1 hour to retrofit, changes log output format.
**Context:** Phase 2 terminal dashboard could consume structured logs directly instead of parsing JSON files from logs/cycle_NNN/.
**Depends on:** Nothing.
**Effort:** S (1-2 hours)
**Priority:** P2

### Dry-run / offline mode
**What:** A mode where the orchestrator runs against a mock world model (static JSON) and skips the mission subprocess. Tests the full LLM loop without Gazebo.
**Why:** Can't iterate on orchestrator logic without launching Gazebo (10+ seconds startup). This would enable fast dev iteration and CI testing.
**Pros:** Faster dev iteration, enables CI, easier to debug LLM prompts.
**Cons:** ~2-3 hours to implement mock world model + skip flags.
**Context:** Evaluator and code writer are already testable in isolation. This closes the gap for full-loop testing. Phase 0 null safety makes this feasible since the orchestrator will handle mock data gracefully.
**Depends on:** Phase 0 null propagation guards.
**Effort:** M (2-3 hours)
**Priority:** P2
