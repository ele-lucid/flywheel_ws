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

## What the Robot is Learning






#
#
#
#
#
### Cycle 7 (Score: 32.8)

**What worked:**
- The robot did not collide with any obstacles, achieving a collision_score of 100.
- The robot covered 58 cells, achieving a partial coverage_score of 16.6.

**What didn't work:**
- The robot failed to visit any goals, resulting in a goals_score of 0.0.
- The robot timed out and did not complete the mission, as indicated by the 'timed_out' flag being true.
- The robot's efficiency score was 0, suggesting inefficient path planning or execution.

**Root causes:**
- The waypoint generation strategy did not account for goal locations, leading to a failure to visit any goals.
- The robot's state machine and recovery strategies were not effective in completing the mission within the time limit.

**Lessons learned:**
- Integrate goal locations into the waypoint generation to ensure goals are prioritized in the path.
- Enhance the state machine to dynamically adjust strategies based on time constraints and proximity to goals.
- Optimize the lawnmower pattern or consider alternative path planning strategies that balance coverage with goal acquisition.

**Cells covered: 58/350** (16% of arena)
