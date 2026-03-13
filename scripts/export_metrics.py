#!/usr/bin/env python3
"""Export flywheel cycle metrics to CSV and print a summary table."""

import json
import os
import sys

WS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(WS_DIR, 'logs')


def load_cycles():
    cycles = []
    if not os.path.exists(LOGS_DIR):
        return cycles

    for name in sorted(os.listdir(LOGS_DIR)):
        if not name.startswith('cycle_'):
            continue
        cycle_dir = os.path.join(LOGS_DIR, name)
        eval_path = os.path.join(cycle_dir, 'evaluation.json')
        summary_path = os.path.join(cycle_dir, 'cycle_summary.json')

        if not os.path.exists(eval_path):
            continue

        with open(eval_path) as f:
            evaluation = json.load(f)

        summary = {}
        if os.path.exists(summary_path):
            with open(summary_path) as f:
                summary = json.load(f)

        cycles.append({
            'cycle': name,
            'score': evaluation.get('total_score', 0),
            'goals': len(evaluation.get('details', {}).get('goals_visited', [])),
            'collisions': evaluation.get('details', {}).get('collision_count', 0),
            'distance': evaluation.get('details', {}).get('total_distance', 0),
            'duration': evaluation.get('details', {}).get('duration', 0),
            'crashed': evaluation.get('details', {}).get('crashed', False),
            'llm_calls': summary.get('llm_calls', 0),
        })

    return cycles


def main():
    cycles = load_cycles()
    if not cycles:
        print("No cycle data found.")
        sys.exit(0)

    # Print table
    header = f"{'Cycle':<12} {'Score':>6} {'Goals':>6} {'Collis':>7} {'Dist':>7} {'Time':>6} {'Crash':>6} {'LLM':>5}"
    print(header)
    print('-' * len(header))

    for c in cycles:
        crash_str = 'YES' if c['crashed'] else ''
        print(f"{c['cycle']:<12} {c['score']:>6.1f} {c['goals']:>6} {c['collisions']:>7} "
              f"{c['distance']:>7.1f} {c['duration']:>6.1f} {crash_str:>6} {c['llm_calls']:>5}")

    # Summary
    scores = [c['score'] for c in cycles]
    print(f"\nTotal cycles: {len(cycles)}")
    print(f"Best score: {max(scores):.1f}")
    print(f"Average score: {sum(scores)/len(scores):.1f}")
    print(f"Improvement: {scores[-1] - scores[0]:+.1f} (first to last)")

    # Export CSV
    csv_path = os.path.join(WS_DIR, 'metrics.csv')
    with open(csv_path, 'w') as f:
        f.write('cycle,score,goals,collisions,distance,duration,crashed,llm_calls\n')
        for c in cycles:
            f.write(f"{c['cycle']},{c['score']},{c['goals']},{c['collisions']},"
                    f"{c['distance']},{c['duration']},{c['crashed']},{c['llm_calls']}\n")
    print(f"\nCSV exported to: {csv_path}")


if __name__ == '__main__':
    main()
