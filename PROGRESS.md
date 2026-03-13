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

## What the Robot is Learning








#
#
#
#
#
#
#
### Cycle 17 (Score: 43.5)

**What worked:**
- The robot avoided collisions successfully, achieving a collision_score of 100.
- The robot's recovery and obstacle avoidance mechanisms prevented crashes, as indicated by the 'crashed' flag being false.

**What didn't work:**
- The robot did not visit any goals, achieving a goals_score of 0.0.
- The mission timed out, indicating inefficiency in task completion.
- The robot did not achieve full coverage, visiting only 133 cells out of a target of 350.

**Root causes:**
- The waypoint navigation strategy did not prioritize goal locations, leading to a lack of goal visits.
- The robot's state machine and recovery logic consumed excessive time, contributing to the mission timeout.

**Lessons learned:**
- Implement a goal prioritization mechanism to ensure goals are visited during the mission.
- Optimize the state machine transitions and recovery logic to reduce time spent in non-productive states.
- Adjust the waypoint generation strategy to improve coverage efficiency and ensure all areas are visited.

**Cells covered: 133/350** (38% of arena)
