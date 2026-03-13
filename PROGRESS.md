# Flywheel Learning Progress

Autonomous learning log. The robot iterates on its own mission code to maximize coverage of a 20x20m arena with obstacles.

## Score History

| Cycle | Score | Cells | Distance | Collisions | Goals |
|-------|-------|-------|----------|------------|-------|
| 1 | **31.9** | 52 | 88.7m | 0 | 0 |

## What the Robot is Learning

### Cycle 1 (Score: 31.9)

**What worked:**
- The robot avoided collisions successfully, as indicated by a collision_score of 100 and a collision_count of 0.

**What didn't work:**
- The robot did not visit any goals, resulting in a goals_score of 0.0.
- The robot's efficiency_score was 0, indicating inefficient navigation.
- The mission timed out without completing all objectives.

**Root causes:**
- The waypoint navigation strategy did not account for goal locations, leading to no goals being visited.
- The robot's path was inefficient, possibly due to ineffective waypoint sequencing and lack of dynamic path adjustment.

**Lessons learned:**
- Incorporate goal locations into the waypoint generation to ensure goals are visited.
- Implement a more dynamic path planning algorithm that adjusts to the environment and goals.
- Enhance the stuck detection and recovery strategy to prevent timeouts and improve efficiency.

**Cells covered: 52/350** (14% of arena)
