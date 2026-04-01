#!/usr/bin/env python3
"""
Self-improvement loop for the OfficeQA agent.

Workflow:
  1. Run arena test on all 20 samples (baseline)
  2. For each failure, ask Claude to analyze the trajectory and suggest a skill patch
  3. Apply the patch and re-run just that task to verify
  4. If it passes → keep; if still failing → revert
  5. Final regression run to check nothing broke
  6. Commit all verified patches to git

Usage:
  export ANTHROPIC_API_KEY=sk-ant-...
  python3 self_improve.py

  # Skip the baseline run and analyze a specific existing run:
  python3 self_improve.py --run-dir .arena/runs/run-20260323-XXXX
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import anthropic
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "anthropic", "-q"], check=True)
    import anthropic

PROJECT_DIR = Path(__file__).parent
SAMPLES_DIR = PROJECT_DIR / ".arena" / "samples"
SKILLS_DIR = PROJECT_DIR / "skills"
RUNS_DIR = PROJECT_DIR / ".arena" / "runs"

# Tasks that cannot be fixed (e.g. require visual/chart parsing)
SKIP_TASKS = {"officeqa-uid0030"}

SKILL_FILES = [
    "01_corpus_structure.md",
    "02_fiscal_year_and_dates.md",
    "03_number_parsing.md",
    "04_question_patterns.md",
    "05_external_knowledge.md",
]


# ── Arena helpers ─────────────────────────────────────────────────────────────

def run_arena_test(tag: str, filter_task: Optional[str] = None, timeout: int = 600) -> Optional[Path]:
    cmd = [".venv/bin/arena", "test", "--tag", tag, "--all"]
    if filter_task:
        cmd += ["--filter", filter_task]
    env = os.environ.copy()
    # Ensure Docker CLI is in PATH
    extra_paths = ["/usr/local/bin", "/Applications/Docker.app/Contents/Resources/bin"]
    current_path = env.get("PATH", "")
    env["PATH"] = ":".join(extra_paths) + ":" + current_path
    subprocess.run(cmd, cwd=PROJECT_DIR, env=env, timeout=timeout)
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
    exceptions = evals[key].get("exception_stats", {})
    # Tasks that errored (e.g. docker not found) count as failed
    errored = [x.split("__")[0] for v in exceptions.values() for x in v]
    return {
        "passed": [x.split("__")[0] for x in rw.get("1.0", [])],
        "failed": list(set([x.split("__")[0] for x in rw.get("0.0", [])] + errored)),
    }


def load_trajectory(run_dir: Path, task_id: str) -> Optional[dict]:
    files = list(run_dir.glob(f"*/{task_id}*/agent/trajectory.json"))
    if not files:
        return None
    with open(files[0]) as f:
        return json.load(f)


# ── Task metadata ──────────────────────────────────────────────────────────────

def load_task(task_id: str) -> dict:
    task_dir = SAMPLES_DIR / task_id
    instruction = ""
    if (task_dir / "instruction.md").exists():
        instruction = (task_dir / "instruction.md").read_text()
    expected = ""
    solve = task_dir / "solution" / "solve.sh"
    if solve.exists():
        m = re.search(r"cat > /app/answer\.txt << 'EOF'\n(.*?)\nEOF", solve.read_text(), re.DOTALL)
        if m:
            expected = m.group(1).strip()
    return {"task_id": task_id, "instruction": instruction, "expected": expected}


# ── Trajectory summariser ──────────────────────────────────────────────────────

def summarize_trajectory(traj: dict, max_chars: int = 7000) -> str:
    lines = []
    for step in traj.get("steps", []):
        msg = step.get("message", "")
        if msg and msg != "(tool use)":
            lines.append(f"[agent] {msg[:300]}")
        for tc in step.get("tool_calls", []):
            lines.append(f"  [tool:{tc.get('function_name','')}] {str(tc.get('arguments',''))[:250]}")
        for r in step.get("observation", {}).get("results", []):
            c = str(r.get("content", ""))[:300]
            if c:
                lines.append(f"  [result] {c}")
    out = "\n".join(lines)
    return out[:max_chars]


# ── Claude analysis ────────────────────────────────────────────────────────────

def ask_claude(task: dict, traj: dict, existing_skills: str) -> str:
    client = anthropic.Anthropic()
    traj_summary = summarize_trajectory(traj)

    prompt = f"""You are debugging a failed U.S. Treasury Bulletin Q&A task.

== QUESTION ==
{task['instruction'][:1200]}

== EXPECTED ANSWER ==
{task['expected']}

== AGENT TRAJECTORY ==
{traj_summary}

== EXISTING SKILLS (already known) ==
{existing_skills[:3500]}

Your job:
1. Identify the EXACT failure point in the trajectory
2. Write a SHORT (2-5 sentence) skill patch that would have prevented this failure
3. Choose which skills file to add it to
4. Do NOT repeat anything already in the existing skills

Respond in EXACTLY this format (no other text):
FAILURE_MODE: <one line>
SKILL_FILE: <one of: 01_corpus_structure.md | 02_fiscal_year_and_dates.md | 03_number_parsing.md | 04_question_patterns.md | 05_external_knowledge.md>
PATCH:
<2-5 sentences of actionable skill text>"""

    resp = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


def parse_claude_response(text: str) -> tuple[str, str, str]:
    failure_mode, skill_file, patch_lines = "", "04_question_patterns.md", []
    in_patch = False
    for line in text.splitlines():
        if line.startswith("FAILURE_MODE:"):
            failure_mode = line[len("FAILURE_MODE:"):].strip()
        elif line.startswith("SKILL_FILE:"):
            raw = line[len("SKILL_FILE:"):].strip()
            # Accept partial matches
            for sf in SKILL_FILES:
                if sf in raw or raw in sf:
                    skill_file = sf
                    break
        elif line.startswith("PATCH:"):
            in_patch = True
        elif in_patch:
            patch_lines.append(line)
    return failure_mode, skill_file, "\n".join(patch_lines).strip()


# ── Patch management ───────────────────────────────────────────────────────────

PATCH_MARKER = "## Auto-learned from"


def apply_patch(skill_file: str, patch: str, task_id: str) -> None:
    fp = SKILLS_DIR / skill_file
    if not fp.exists():
        fp = SKILLS_DIR / "04_question_patterns.md"
    with open(fp, "a") as f:
        f.write(f"\n\n{PATCH_MARKER} {task_id}\n{patch}\n")


def revert_patch(skill_file: str, task_id: str) -> None:
    fp = SKILLS_DIR / skill_file
    if not fp.exists():
        return
    content = fp.read_text()
    marker = f"\n\n{PATCH_MARKER} {task_id}\n"
    if marker in content:
        fp.write_text(content[: content.index(marker)])


def load_skills_text() -> str:
    parts = []
    for sf in SKILL_FILES:
        fp = SKILLS_DIR / sf
        if fp.exists():
            parts.append(f"=== {sf} ===\n{fp.read_text()}")
    return "\n\n".join(parts)


# ── Main loop ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="OfficeQA self-improvement loop")
    parser.add_argument("--run-dir", help="Reuse an existing run dir instead of running baseline")
    parser.add_argument("--task", help="Only fix a specific task ID")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    print("=" * 60)
    print("OfficeQA Self-Improvement Loop")
    print("=" * 60)

    # ── Step 1: Baseline ──────────────────────────────────────────────────────
    if args.run_dir:
        run_dir = Path(args.run_dir)
        print(f"Reusing run: {run_dir}")
    else:
        print("\n[1/4] Running baseline arena test (all 20 samples)…")
        run_dir = run_arena_test(f"self-improve-baseline-{ts}", timeout=3600)
        if not run_dir:
            sys.exit("ERROR: Could not find run directory after baseline test")

    baseline = parse_results(run_dir)
    if not baseline:
        sys.exit("ERROR: Could not parse results from run directory")

    failures = [t for t in baseline["failed"] if t not in SKIP_TASKS]
    if args.task:
        failures = [t for t in failures if t == args.task]

    n_total = len(baseline["passed"]) + len(baseline["failed"])
    print(f"Baseline: {len(baseline['passed'])}/{n_total} passed")
    print(f"Fixable failures ({len(failures)}): {failures}")

    if not failures:
        print("\nNo fixable failures found — already at maximum!")
        return

    # ── Step 2: Fix each failure ──────────────────────────────────────────────
    print(f"\n[2/4] Analyzing and patching {len(failures)} failures…")
    fixed, unfixed = [], []

    for task_id in failures:
        print(f"\n  ┌─ {task_id}")
        traj = load_trajectory(run_dir, task_id)
        if not traj:
            print(f"  │  No trajectory found — skipping")
            unfixed.append(task_id)
            continue

        task = load_task(task_id)
        skills = load_skills_text()

        print(f"  │  Q: {task['instruction'][:90].strip()}…")
        print(f"  │  Expected: {task['expected']}")
        print(f"  │  Asking Claude for skill patch…")

        try:
            raw = ask_claude(task, traj, skills)
        except Exception as e:
            print(f"  │  Claude error: {e} — skipping")
            unfixed.append(task_id)
            continue

        failure_mode, skill_file, patch = parse_claude_response(raw)
        print(f"  │  Failure mode : {failure_mode}")
        print(f"  │  Patching file: {skill_file}")
        print(f"  │  Patch preview: {patch[:160].replace(chr(10),' ')}…")

        apply_patch(skill_file, patch, task_id)

        print(f"  │  Re-running {task_id} to verify…")
        try:
            verify_dir = run_arena_test(f"verify-{task_id[:20]}-{ts}", filter_task=task_id, timeout=400)
            verify = parse_results(verify_dir)
        except Exception as e:
            print(f"  │  Verify run failed: {e}")
            revert_patch(skill_file, task_id)
            unfixed.append(task_id)
            continue

        if task_id in verify.get("passed", []):
            print(f"  └─ ✅ FIXED")
            fixed.append((task_id, skill_file, patch))
        else:
            print(f"  └─ ❌ Still failing — reverting patch")
            revert_patch(skill_file, task_id)
            unfixed.append(task_id)

    # ── Step 3: Regression check ──────────────────────────────────────────────
    if fixed:
        print(f"\n[3/4] Regression check (all 20 samples with {len(fixed)} patches applied)…")
        final_dir = run_arena_test(f"self-improve-final-{ts}")
        final = parse_results(final_dir)
        n_after = len(final.get("passed", []))
        n_before = len(baseline["passed"])
        regressions = [t for t in baseline["passed"] if t in final.get("failed", [])]
        if regressions:
            print(f"  ⚠️  Regressions detected: {regressions}")
        else:
            print(f"  ✅ No regressions")
        print(f"  Score: {n_before}/{n_total} → {n_after}/{n_total}")
    else:
        final = baseline

    # ── Step 4: Commit ────────────────────────────────────────────────────────
    print(f"\n[4/4] Summary")
    print(f"  Fixed   : {[t for t, _, _ in fixed]}")
    print(f"  Unfixed : {unfixed}")
    print(f"  Skipped : {list(SKIP_TASKS)}")

    if fixed:
        print(f"\n  Committing {len(fixed)} skill improvements to git…")
        subprocess.run(["git", "add", "skills/"], cwd=PROJECT_DIR)
        body = "\n".join(f"- {t}: added to {sf}" for t, sf, _ in fixed)
        msg = f"auto-improve: patch {len(fixed)} task failure(s)\n\n{body}\n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
        subprocess.run(["git", "commit", "-m", msg], cwd=PROJECT_DIR)
        print("  Committed!")

    print("\nDone.")


if __name__ == "__main__":
    main()
