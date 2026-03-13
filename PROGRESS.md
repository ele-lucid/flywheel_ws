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

## What the Robot is Learning







#
#
#
#
#
#
### Cycle 13 (Score: 33.1)

**What worked:**
- The robot did not collide with any obstacles, achieving a perfect collision score of 100.

**What didn't work:**
- The robot failed to visit any of the 5 goals.
- The robot timed out before completing the mission.
- The robot only covered 17.1% of the area, visiting 60 cells out of a target of 350.

**Root causes:**
- The waypoint navigation strategy did not prioritize goal locations, leading to zero goals being visited.
- The robot's state machine did not handle time management effectively, resulting in a timeout.

**Lessons learned:**
- Integrate goal prioritization into the waypoint navigation to ensure goals are visited.
- Implement a time management strategy that dynamically adjusts the mission plan to avoid timeouts.
- Optimize the coverage pattern to improve efficiency and increase the coverage score.

**Cells covered: 60/350** (17% of arena)
