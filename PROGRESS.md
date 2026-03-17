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
### Cycle 71 (Score: 73.6)

**What worked:**
- The robot achieved 100% collision avoidance, with a collision count of 0.
- The robot maintained high efficiency, covering 309 cells with a total distance of 276.08 meters.

**What didn't work:**
- No goals were visited during the mission despite having 5 goals to achieve.
- The mission timed out after 302.09 seconds, achieving only 30% completion.

**Root causes:**
- The code does not prioritize visiting goals, as the waypoint logic only checks if goals are within 1.5m of the current row, which is insufficient given the goals' locations.
- The mission logic prematurely completes the mission if 320 cells are visited or time exceeds 290 seconds, which does not align with the actual mission timeout at 302.09 seconds.

**Lessons learned:**
- Incorporate goal prioritization by explicitly adding goals as waypoints with a higher priority than coverage waypoints.
- Increase the waypoint reach threshold from 1.0m to 2.0m to ensure goals are reached, as the current threshold is not sufficient for goal proximity.
- Adjust the mission completion condition to check for actual mission timeout at 302.09 seconds instead of 290 seconds.

**Cells covered: 309/350** (88% of arena)
