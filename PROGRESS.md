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
### Cycle 170 (Score: 74.5)

**What worked:**
- The robot had 0 collisions, achieving a 100 collision score.
- The robot maintained high efficiency with a 100 efficiency score.

**What didn't work:**
- The robot timed out without visiting any goals, achieving 0.0 goals score.
- The robot visited 315 cells but did not complete the mission, resulting in only 30 completion score.

**Root causes:**
- The `build_waypoints` method appends goals as initial waypoints but does not prioritize them effectively during execution.
- The `distance_to` threshold of 1.0m for waypoint completion is too large, causing imprecise goal visits.

**Lessons learned:**
- Reduce the waypoint reach threshold from 1.0m to 0.5m to ensure precise goal visitation.
- Re-order waypoints to prioritize goal locations: insert goal (5,5) between y=-9 and y=-8, and goal (-8,7) between y=6 and y=7.
- Modify the `execute` method to dynamically re-evaluate and adjust waypoints based on proximity to goals within 1.5m.

**Cells covered: 315/350** (90% of arena)
