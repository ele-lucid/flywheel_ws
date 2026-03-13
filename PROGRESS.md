# Flywheel Learning Progress

Autonomous learning log. The robot iterates on its own mission code to maximize coverage of a 20x20m arena with obstacles.

## Score History

| Cycle | Score | Cells | Distance | Collisions | Goals |
|-------|-------|-------|----------|------------|-------|
| 1 | **31.9** | 52 | 88.7m | 0 | 0 |
| 2 | **33.6** | 64 | 82.2m | 0 | 0 |
| 3 | **27.2** | 19 | 115.6m | 0 | 0 |
| 5 | **29.8** | 37 | 51.9m | 0 | 0 |

## What the Robot is Learning




#
#
#
### Cycle 5 (Score: 29.8)

**What worked:**
- The robot avoided collisions effectively, achieving a collision_score of 100 and a collision_count of 0.
- The robot completed the mission without crashing, as indicated by the crashed flag being false.

**What didn't work:**
- The robot did not visit any of the 5 goals, resulting in a goals_score of 0.0.
- The mission timed out without achieving full coverage, as indicated by the timed_out flag being true and coverage_score being only 10.6.
- The robot's efficiency was poor, with an efficiency_score of 0, indicating excessive wandering or inefficient path planning.

**Root causes:**
- The waypoint generation strategy did not align with the goal locations, leading to a failure to visit any goals.
- The coverage strategy was inefficient, as the robot only visited 37 cells out of a possible 350, and the mission timed out.

**Lessons learned:**
- Incorporate goal locations into the waypoint generation process to ensure that all goals are visited.
- Improve the coverage strategy by dynamically adjusting waypoints based on unvisited areas to increase coverage efficiency.
- Optimize path planning algorithms to reduce total distance traveled and increase efficiency.

**Cells covered: 37/350** (10% of arena)
