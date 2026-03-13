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

## What the Robot is Learning





#
#
#
#
### Cycle 6 (Score: 31.9)

**What worked:**
- The robot successfully avoided collisions, achieving a collision_score of 100.
- The robot covered 52 cells, contributing to a coverage_score of 14.9.

**What didn't work:**
- The robot did not visit any of the 5 goals, resulting in a goals_score of 0.0.
- The robot timed out before completing the mission, as indicated by 'timed_out': true.
- The robot's efficiency score was 0, indicating inefficient path planning or execution.

**Root causes:**
- The waypoint generation did not account for goal locations, leading to no goals being visited.
- The robot's state machine and recovery mechanisms were inefficient, causing the mission to time out.

**Lessons learned:**
- Incorporate goal locations into the waypoint generation to ensure goals are visited.
- Improve the efficiency of the state machine by optimizing recovery and obstacle avoidance strategies.
- Adjust velocity parameters to enhance path efficiency and reduce mission duration.

**Cells covered: 52/350** (14% of arena)
