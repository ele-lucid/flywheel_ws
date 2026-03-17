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
### Cycle 110 (Score: 74.1)

**What worked:**
- The robot achieved a collision_score of 100, indicating no collisions occurred.
- The robot visited 312 cells, achieving a coverage_score of 89.1.

**What didn't work:**
- The robot did not visit any goals, resulting in a goals_score of 0.0.
- The mission timed out, achieving only 30% completion.

**Root causes:**
- The waypoint navigation logic in 'build_waypoints' does not prioritize goal coordinates, leading to no goals being visited.
- The condition 'if len(self.visited_cells) >= 320 or self.elapsed_time() > 290:' triggers a premature mission completion, limiting time to visit goals.

**Lessons learned:**
- Modify 'build_waypoints' to ensure goals are prioritized by inserting them directly at the start of the waypoint list.
- Adjust the mission timeout condition to 'self.elapsed_time() > 350' to allow more time for goal visits.
- Add a check in 'execute' to prioritize moving to the nearest unvisited goal if within 5.0m, before continuing with waypoint navigation.

**Cells covered: 312/350** (89% of arena)
