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
### Cycle 124 (Score: 74.2)

**What worked:**
- The robot had zero collisions, resulting in a collision_score of 100.
- The robot covered 313 cells, achieving a coverage_score of 89.4.

**What didn't work:**
- No goals were visited, resulting in a goals_score of 0.0.
- The mission timed out at 302.1 seconds, leading to a completion_score of 30.

**Root causes:**
- The waypoint navigation logic does not prioritize goal locations, as goals are only added if they are within 1.5m of the current row in 'build_waypoints'.
- The robot's state machine does not have a mechanism to prioritize or revisit unvisited goals, leading to a lack of goal visits.

**Lessons learned:**
- Modify the 'build_waypoints' method to always include goals as waypoints, regardless of their distance to the current row, ensuring all goals are visited.
- Introduce a goal prioritization mechanism in the state machine to periodically check and navigate to the nearest unvisited goal.
- Adjust the timeout condition in 'execute' to check for time elapsed more frequently, ensuring the mission completes before 290 seconds.

**Cells covered: 313/350** (89% of arena)
