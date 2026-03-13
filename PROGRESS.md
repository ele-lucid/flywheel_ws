# Flywheel Learning Progress

Autonomous learning log. The robot iterates on its own mission code to maximize coverage of a 20x20m arena with obstacles.

## Score History

| Cycle | Score | Cells | Distance | Collisions | Goals |
|-------|-------|-------|----------|------------|-------|
| 1 | **31.9** | 52 | 88.7m | 0 | 0 |
| 2 | **33.6** | 64 | 82.2m | 0 | 0 |

## What the Robot is Learning


#
### Cycle 2 (Score: 33.6)

**What worked:**
- The robot successfully avoided collisions, with a collision_score of 100 and collision_count of 0.
- The robot was able to recover from stuck conditions without crashing, as evidenced by 'crashed' being false.

**What didn't work:**
- The robot did not visit any goals, resulting in a goals_score of 0.0.
- The mission timed out without completing all waypoints, as indicated by the 'timed_out' flag being true.
- The robot's efficiency score was 0, indicating inefficient path planning or execution.

**Root causes:**
- The waypoint generation and navigation logic did not account for goal locations, leading to no goals being visited.
- The robot's path planning did not efficiently cover the arena, leading to a timeout before completing the mission.

**Lessons learned:**
- Incorporate goal locations into waypoint planning to ensure goals are visited.
- Optimize path planning algorithms to ensure more efficient coverage of the arena, possibly by implementing a more sophisticated search pattern.
- Improve the robot's movement logic to enhance efficiency, such as by minimizing unnecessary turns and optimizing speed settings.

**Cells covered: 64/350** (18% of arena)
