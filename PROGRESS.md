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
| 342 | **79.5** | 495 | 432.5m | 0 | 0 |

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
#
### Cycle 342 (Score: 79.5)

**What worked:**
- The robot achieved 100% coverage, visiting 495 cells.
- There were no collisions, as indicated by a collision_score of 100.

**What didn't work:**
- The robot failed to visit any of the 5 goals, resulting in a goals_score of 0.0.
- The mission timed out at 302.04 seconds, achieving only 30% completion.

**Root causes:**
- The logic for visiting goals is flawed; goals are appended to waypoints based on proximity to rows, but none were reached due to the waypoint execution order and timing.
- The mission's timeout logic triggers at 290 seconds, but the robot was still executing waypoints without prioritizing goal visits.

**Lessons learned:**
- Modify the waypoint order to prioritize visiting goals by inserting goal (5,5) before row y=5 and goal (-8,7) before row y=7.
- Increase the timeout threshold to 350 seconds to allow more time for goal visits.
- Adjust the waypoint reach threshold from 1.0m to 0.5m for better precision in goal proximity detection.

**Cells covered: 495/350** (141% of arena)
