#!/usr/bin/env python3
"""
Quick analyzer for arena test runs.

Usage:
  python3 analyze_run.py                           # analyze latest run
  python3 analyze_run.py .arena/runs/run-XXXXXX    # analyze specific run
  python3 analyze_run.py --compare run1 run2       # compare two runs
"""

import json
import re
import sys
from pathlib import Path

SAMPLES_DIR = Path(__file__).parent / ".arena" / "samples"
RUNS_DIR = Path(__file__).parent / ".arena" / "runs"


def get_latest_run() -> Path:
    runs = sorted(RUNS_DIR.glob("run-*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return runs[0] if runs else None


def parse_results(run_dir: Path) -> dict:
    files = list(run_dir.glob("*/result.json"))
    if not files:
        return {}
    with open(files[0]) as f:
        d = json.load(f)
    evals = d.get("stats", {}).get("evals", {})
    if not evals:
        return {}
    key = list(evals.keys())[0]
    rw = evals[key].get("reward_stats", {}).get("reward", {})
    cost = d.get("stats", {}).get("cost", {})
    return {
        "passed": sorted([x.split("__")[0] for x in rw.get("1.0", [])]),
        "failed": sorted([x.split("__")[0] for x in rw.get("0.0", [])]),
        "cost": cost,
    }


def load_task_instruction(task_id: str) -> str:
    path = SAMPLES_DIR / task_id / "instruction.md"
    if path.exists():
        return path.read_text()[:200].strip()
    return "(no instruction)"


def load_expected(task_id: str) -> str:
    solve = SAMPLES_DIR / task_id / "solution" / "solve.sh"
    if solve.exists():
        m = re.search(r"cat > /app/answer\.txt << 'EOF'\n(.*?)\nEOF", solve.read_text(), re.DOTALL)
        if m:
            return m.group(1).strip()
    return "(unknown)"


def extract_agent_answer(run_dir: Path, task_id: str) -> str:
    files = list(run_dir.glob(f"*/{task_id}*/agent/trajectory.json"))
    if not files:
        return "(no trajectory)"
    with open(files[0]) as f:
        traj = json.load(f)
    for step in reversed(traj.get("steps", [])):
        for tc in step.get("tool_calls", []):
            args = str(tc.get("arguments", ""))
            if "answer.txt" in args:
                m = re.search(r'echo ["\']?(.+?)["\']?\s*>\s*/app/answer', args)
                if m:
                    return m.group(1).strip()
    return "(could not extract)"


def analyze(run_dir: Path):
    print(f"\n{'='*60}")
    print(f"Run: {run_dir.name}")
    print(f"{'='*60}")
    
    results = parse_results(run_dir)
    if not results:
        print("ERROR: Could not parse results")
        return
    
    n_total = len(results["passed"]) + len(results["failed"])
    print(f"\nScore: {len(results['passed'])}/{n_total} passed ({100*len(results['passed'])/n_total:.1f}%)")
    
    if results.get("cost"):
        print(f"Cost:  ${results['cost'].get('total', 0):.2f}")
    
    print(f"\n✅ Passed ({len(results['passed'])}):")
    for t in results["passed"]:
        print(f"   {t}")
    
    print(f"\n❌ Failed ({len(results['failed'])}):")
    for t in results["failed"]:
        expected = load_expected(t)
        got = extract_agent_answer(run_dir, t)
        instruction = load_task_instruction(t)
        print(f"   {t}")
        print(f"      Q: {instruction[:100]}...")
        print(f"      Expected: {expected}")
        print(f"      Got:      {got}")
        print()


def compare(run1: Path, run2: Path):
    r1 = parse_results(run1)
    r2 = parse_results(run2)
    
    print(f"\n{'='*60}")
    print(f"Comparison: {run1.name} vs {run2.name}")
    print(f"{'='*60}")
    
    s1 = set(r1.get("passed", []))
    s2 = set(r2.get("passed", []))
    
    gained = s2 - s1
    lost = s1 - s2
    
    print(f"\nRun 1: {len(s1)} passed")
    print(f"Run 2: {len(s2)} passed")
    print(f"Net:   {'+' if len(s2) >= len(s1) else ''}{len(s2) - len(s1)}")
    
    if gained:
        print(f"\n🆕 Gained in run 2:")
        for t in sorted(gained):
            print(f"   {t}")
    
    if lost:
        print(f"\n🔻 Lost in run 2 (regressions):")
        for t in sorted(lost):
            print(f"   {t}")


if __name__ == "__main__":
    args = sys.argv[1:]
    
    if "--compare" in args:
        idx = args.index("--compare")
        r1 = Path(args[idx + 1])
        r2 = Path(args[idx + 2])
        compare(r1, r2)
    elif args:
        analyze(Path(args[0]))
    else:
        run_dir = get_latest_run()
        if run_dir:
            analyze(run_dir)
        else:
            print("No runs found in .arena/runs/")
