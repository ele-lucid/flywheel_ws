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

## What the Robot is Learning









#
#
#
#
#
#
#
#
### Cycle 20 (Score: 44.9)

**What worked:**
- The robot successfully avoided collisions, achieving a collision_score of 100.
- The robot was able to execute the lawnmower pattern without crashing, as indicated by 'crashed' being false.

**What didn't work:**
- The robot failed to visit any of the 5 goals, resulting in a goals_score of 0.0.
- The robot timed out without completing the mission, as indicated by the 'timed_out' flag being true.
- The coverage score was only 40.9, indicating that the robot did not cover a significant portion of the arena.

**Root causes:**
- The waypoint navigation logic did not prioritize goal locations, leading to zero goals being visited.
- The mission timed out due to inefficient path planning and possibly redundant waypoint loops.

**Lessons learned:**
- Incorporate goal prioritization into the waypoint navigation logic to ensure goals are visited.
- Optimize the path planning algorithm to reduce redundancy and improve efficiency in completing the mission within the time limit.
- Expand the waypoint generation logic to ensure full coverage of the arena, and adjust the mission termination conditions to allow more time if necessary.

**Cells covered: 143/350** (40% of arena)
