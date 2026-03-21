#!/usr/bin/env python3
"""
Analyze arena test run results and trajectories to identify failure patterns.
Usage: python3 analyze_run.py [run-id]
       python3 analyze_run.py          # analyzes the latest run
"""
import json
import sys
from pathlib import Path

RUNS_DIR = Path(".arena/runs")


def latest_run() -> Path:
    runs = sorted(RUNS_DIR.glob("run-*/"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not runs:
        print("No runs found.")
        sys.exit(1)
    return runs[0]


def analyze(run_dir: Path):
    results_file = run_dir / "results.json"
    if not results_file.exists():
        print(f"No results.json in {run_dir}")
        return

    results = json.loads(results_file.read_text())
    print(f"\n{'='*60}")
    print(f"RUN: {results['run_id']}")
    print(f"SCORE: {results['score']*100:.1f}%  ({results['tasks_passed']}/{results['tasks_total']} passed)")
    print(f"COST:  ${results['total_cost_usd']:.4f} total  (${results['avg_cost_usd']:.4f}/task avg)")
    print(f"TIME:  {results['avg_latency_sec']:.0f}s avg per task")

    for task in results.get("tasks", []):
        tid = task["task_id"]
        status = "✓ PASS" if task["reward"] > 0 else "✗ FAIL"
        cost = task.get("cost_usd", 0)
        latency = task.get("latency_sec", 0)
        print(f"\n  {status}  {tid}  (${cost:.4f}, {latency:.0f}s)")
        if task.get("error"):
            err = task["error"][:200]
            print(f"    ERROR: {err}")

        # Try to find and read the trajectory
        trial_dirs = list(run_dir.glob(f"**/{tid}__*/"))
        for trial_dir in trial_dirs:
            _analyze_trial(trial_dir)


def _analyze_trial(trial_dir: Path):
    # Read agent answer
    answer_clue = None
    traj_file = trial_dir / "agent" / "trajectory.json"
    if traj_file.exists():
        try:
            traj = json.loads(traj_file.read_text())
            steps = traj if isinstance(traj, list) else traj.get("steps", [])
            # Find the last tool call and the final answer written
            tool_calls = []
            for step in steps:
                role = step.get("role") or step.get("type", "")
                content = step.get("content", "")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_calls.append(block.get("name", "unknown"))
            if tool_calls:
                print(f"    TOOLS CALLED: {', '.join(tool_calls[-10:])}")
        except Exception:
            pass

    # Read opencode log for answer written
    opencode_log = trial_dir / "agent" / "opencode.txt"
    if opencode_log.exists():
        log = opencode_log.read_text(errors="replace")
        # Find answer.txt write
        if "answer.txt" in log:
            lines = [l for l in log.split("\n") if "answer.txt" in l]
            print(f"    ANSWER LINES: {lines[-3:] if lines else 'none'}")

    # Read verifier result
    result_file = trial_dir / "result.json"
    if result_file.exists():
        try:
            r = json.loads(result_file.read_text())
            agent_res = r.get("agent_result", {})
            print(f"    TOKENS: {agent_res.get('n_input_tokens',0):,} in / {agent_res.get('n_output_tokens',0):,} out")
            verifier = r.get("verifier_result", {})
            print(f"    VERIFIER: {verifier}")
        except Exception:
            pass


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_id = sys.argv[1]
        run_dir = RUNS_DIR / run_id
        # also check nested
        candidates = list(RUNS_DIR.glob(f"**/{run_id}/"))
        if candidates:
            run_dir = candidates[0]
    else:
        run_dir = latest_run()
        # check for nested run dir
        inner = list(run_dir.glob("run-*/"))
        if inner:
            run_dir = inner[0]

    analyze(run_dir)
