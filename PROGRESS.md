# Flywheel Learning Progress

Autonomous learning log. The robot iterates on its own mission code to maximize coverage of a 20x20m arena with obstacles.

## Score History

| Cycle | Score | Cells | Distance | Collisions | Goals |
|-------|-------|-------|----------|------------|-------|
| 1 | **31.9** | 52 | 88.7m | 0 | 0 |
| 2 | **33.6** | 64 | 82.2m | 0 | 0 |
| 3 | **27.2** | 19 | 115.6m | 0 | 0 |
| 5 | **29.8** | 37 | 51.9m | 0 | 0 |
| 6 | **31.9** | 52 | 55.1m | 0 | 0 |
| 7 | **32.8** | 58 | 56.5m | 0 | 0 |
| 13 | **33.1** | 60 | 58.5m | 0 | 0 |
| 17 | **43.5** | 133 | 118.7m | 0 | 0 |
| 20 | **44.9** | 143 | 121.5m | 0 | 0 |
| 62 | **54.9** | 178 | 158.9m | 0 | 0 |
| 66 | **59.6** | 211 | 199.8m | 0 | 0 |
| 71 | **73.6** | 309 | 276.1m | 0 | 0 |
| 110 | **74.1** | 312 | 297.0m | 0 | 0 |
| 124 | **74.2** | 313 | 312.1m | 0 | 0 |
| 170 | **74.5** | 315 | 284.2m | 0 | 0 |
| 300 | **78.5** | 343 | 345.0m | 0 | 0 |

## What the Robot is Learning
















#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
### Cycle 300 (Score: 78.5)

**What worked:**
- Achieved 98% coverage of the arena, visiting 343 out of 350 cells.
- No collisions occurred during the mission, indicating effective obstacle avoidance.

**What didn't work:**
- No goals were visited despite being in close proximity during coverage.
- The mission timed out at 302.05 seconds without visiting any goals.

**Root causes:**
- The waypoint generation logic in 'build_waypoints' does not prioritize goals effectively, as goals are only added if they are within 1.5m of the current row.
- The 'distance_to' function's threshold of 0.8m for marking goals as visited is too small, given that goals were not registered as visited.

**Lessons learned:**
- Increase the goal proximity threshold in 'distance_to' from 0.8m to 1.5m to ensure goals are marked as visited when in close proximity.
- Modify 'build_waypoints' to ensure goals are inserted as waypoints at specific intervals, such as between row y=4 and y=5 for goal (5,5), and between row y=6 and y=7 for goal (-8,7).
- Adjust the timeout condition to allow for more time to complete the mission, as the current time limit of 290 seconds before timeout is too restrictive given the coverage achieved.

**Cells covered: 343/350** (98% of arena)
