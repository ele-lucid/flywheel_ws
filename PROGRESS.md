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
### Cycle 62 (Score: 54.9)

**What worked:**
- No collisions occurred, resulting in a collision_score of 100.
- High efficiency with a total distance of 158.95 meters and efficiency_score of 100.

**What didn't work:**
- The robot did not visit any goals, resulting in a goals_score of 0.0.
- Coverage was only 50.9%, with 178 cells visited out of 350 reachable cells.
- The mission timed out at 122.1 seconds, earning only 30/100 completion score.

**Root causes:**
- Waypoints were generated without prioritizing goal locations, leading to missed goals.
- The coverage logic terminates at 320 cells or 110 seconds, but only 178 cells were visited within the timeout.

**Lessons learned:**
- Insert goal (5,5) as a waypoint between row y=4 and y=5, and goal (-8,7) between row y=6 and y=7, to visit goals during coverage without detours.
- Increase the coverage completion threshold from 320 to 350 cells to ensure full arena coverage.
- Adjust the timeout threshold from 110 seconds to 140 seconds to allow more time for goal visits and coverage.

**Cells covered: 178/350** (50% of arena)
