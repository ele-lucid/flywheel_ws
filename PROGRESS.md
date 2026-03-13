# Flywheel Learning Progress

Autonomous learning log. The robot iterates on its own mission code to maximize coverage of a 20x20m arena with obstacles.

## Score History

| Cycle | Score | Cells | Distance | Collisions | Goals |
|-------|-------|-------|----------|------------|-------|
| 1 | **31.9** | 52 | 88.7m | 0 | 0 |
| 2 | **33.6** | 64 | 82.2m | 0 | 0 |
| 3 | **27.2** | 19 | 115.6m | 0 | 0 |

## What the Robot is Learning



#
#
### Cycle 3 (Score: 27.2)

**What worked:**
- The robot did not collide with any obstacles, achieving a collision_score of 100.
- The mission completed successfully without crashing.

**What didn't work:**
- The robot did not visit any goals, resulting in a goals_score of 0.0.
- The robot only covered 19 cells, leading to a low coverage_score of 5.4.
- The mission timed out, indicating inefficiency in task completion.

**Root causes:**
- The robot's waypoint navigation did not align with the goal locations, preventing goal visitation.
- The coverage strategy was inefficient, covering only 19 cells in 92.01 seconds.

**Lessons learned:**
- Integrate goal locations into the waypoint generation logic to ensure goals are visited.
- Enhance the coverage algorithm to increase the number of cells visited within the time limit.
- Implement a more efficient path planning strategy to optimize coverage and goal visitation.

**Cells covered: 19/350** (5% of arena)
