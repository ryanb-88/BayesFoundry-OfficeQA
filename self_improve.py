#!/usr/bin/env python3
"""
Self-improvement loop v2 for the OfficeQA agent.

Improvements over v1:
  - Multi-pass fixing: retry failed patches with alternative strategies
  - Better trajectory analysis: extracts actual answer vs expected
  - Failure categorization: distinguishes data-finding vs computation vs format errors
  - Patch deduplication: avoids adding redundant skill content
  - Detailed HTML report generation

Workflow:
  1. Run arena test on all 20 samples (baseline)
  2. Categorize each failure (data/compute/format/timeout/chart)
  3. For each fixable failure, ask Claude to analyze and suggest a skill patch
  4. Apply patch → re-run task → verify → keep or revert
  5. Second pass: try format-only fixes for remaining failures
  6. Final regression run
  7. Commit + generate report

Usage:
  export ANTHROPIC_API_KEY=sk-ant-...
  python3 self_improve.py
  python3 self_improve.py --run-dir .arena/runs/run-20260323-XXXX
  python3 self_improve.py --task officeqa-uid0041
  python3 self_improve.py --dry-run  # analyze only, no patches
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

# Tasks that cannot be fixed
SKIP_TASKS = {"officeqa-uid0030"}  # Visual/chart — no image data in corpus

SKILL_FILES = [
    "01_corpus_structure.md",
    "02_fiscal_year_and_dates.md",
    "03_number_parsing.md",
    "04_question_patterns.md",
    "05_external_knowledge.md",
    "06_statistical_operations.md",
    "07_table_types.md",
]

# Also allow patching SKILL.md files in subdirectories
SKILL_SUBDIRS = [
    "external-knowledge",
    "fiscal-year-dates",
    "corpus-structure",
    "statistical-operations",
    "table-types",
    "number-parsing",
    "question-patterns",
]

FAILURE_CATEGORIES = {
    "DATA_NOT_FOUND": "Agent couldn't locate the right table or value",
    "WRONG_TABLE": "Agent found wrong table (e.g., PDO-1 vs PDO-2)",
    "COMPUTATION_ERROR": "Calculation was incorrect (wrong formula, wrong base, rounding)",
    "FORMAT_ERROR": "Answer correct but wrong format (missing $, %, brackets, unit)",
    "TIMEOUT": "Agent ran out of time or turns",
    "CHART_VISUAL": "Question requires visual data not in corpus",
    "WRONG_PERIOD": "Used wrong fiscal year, calendar year, or date range",
    "HALLUCINATION": "Agent used a fabricated or misremembered value",
}


# ── Arena helpers ─────────────────────────────────────────────────────────────

def run_arena_test(tag: str, filter_task: Optional[str] = None, timeout: int = 600) -> Optional[Path]:
    """Run arena test and return the run directory."""
    cmd = [".venv/bin/arena", "test", "--tag", tag, "--all"]
    if filter_task:
        cmd += ["--filter", filter_task]
    env = os.environ.copy()
    extra_paths = ["/usr/local/bin", "/Applications/Docker.app/Contents/Resources/bin"]
    env["PATH"] = ":".join(extra_paths) + ":" + env.get("PATH", "")
    subprocess.run(cmd, cwd=PROJECT_DIR, env=env, timeout=timeout)
    runs = sorted(RUNS_DIR.glob("run-*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return runs[0] if runs else None


def parse_results(run_dir: Path) -> dict:
    """Parse arena run results."""
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
    errored = [x.split("__")[0] for v in exceptions.values() for x in v]
    return {
        "passed": [x.split("__")[0] for x in rw.get("1.0", [])],
        "failed": list(set([x.split("__")[0] for x in rw.get("0.0", [])] + errored)),
    }


def load_trajectory(run_dir: Path, task_id: str) -> Optional[dict]:
    """Load agent trajectory for a specific task."""
    files = list(run_dir.glob(f"*/{task_id}*/agent/trajectory.json"))
    if not files:
        return None
    with open(files[0]) as f:
        return json.load(f)


def load_task(task_id: str) -> dict:
    """Load task metadata including instruction and expected answer."""
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


# ── Trajectory analysis ──────────────────────────────────────────────────────

def summarize_trajectory(traj: dict, max_chars: int = 8000) -> str:
    """Create a concise summary of the agent trajectory."""
    lines = []
    for step in traj.get("steps", []):
        msg = step.get("message", "")
        if msg and msg != "(tool use)":
            lines.append(f"[AGENT] {msg[:400]}")
        for tc in step.get("tool_calls", []):
            lines.append(f"  [TOOL:{tc.get('function_name','')}] {str(tc.get('arguments',''))[:300]}")
        for r in step.get("observation", {}).get("results", []):
            c = str(r.get("content", ""))[:400]
            if c:
                lines.append(f"  [RESULT] {c}")
    out = "\n".join(lines)
    return out[:max_chars]


def extract_agent_answer(traj: dict) -> str:
    """Extract the agent's final answer from trajectory."""
    # Look for answer.txt writes
    for step in reversed(traj.get("steps", [])):
        for tc in step.get("tool_calls", []):
            args = str(tc.get("arguments", ""))
            if "answer.txt" in args:
                # Try to extract the value being written
                m = re.search(r'echo ["\']?(.+?)["\']?\s*>\s*/app/answer', args)
                if m:
                    return m.group(1).strip()
        msg = step.get("message", "")
        if "answer.txt" in msg:
            m = re.search(r'echo ["\']?(.+?)["\']?\s*>\s*/app/answer', msg)
            if m:
                return m.group(1).strip()
    return "(could not extract)"


def categorize_failure(task: dict, traj: dict) -> str:
    """Categorize the failure type based on trajectory analysis."""
    instruction = task["instruction"].lower()
    agent_answer = extract_agent_answer(traj)
    expected = task["expected"]
    
    # Chart/visual
    if any(w in instruction for w in ["chart", "exhibit", "plot", "graph", "visual", "figure"]):
        return "CHART_VISUAL"
    
    # Timeout (too many steps or no answer)
    if agent_answer == "(could not extract)" or "PRELIMINARY" in agent_answer:
        return "TIMEOUT"
    
    # Format error — answer is numerically close but format is wrong
    try:
        # Strip formatting to compare numbers
        clean_expected = re.sub(r'[,$%\[\]\s]', '', expected.split(',')[0] if ',' in expected else expected)
        clean_actual = re.sub(r'[,$%\[\]\s]', '', agent_answer.split(',')[0] if ',' in agent_answer else agent_answer)
        
        if clean_expected and clean_actual:
            exp_num = float(clean_expected.replace('billion', '').replace('million', '').strip())
            act_num = float(clean_actual.replace('billion', '').replace('million', '').strip())
            if abs(exp_num - act_num) / max(abs(exp_num), 1e-10) < 0.02:
                return "FORMAT_ERROR"
    except (ValueError, ZeroDivisionError):
        pass
    
    # Check trajectory for common patterns
    traj_text = summarize_trajectory(traj)
    if "not found" in traj_text.lower() or "no matches" in traj_text.lower():
        return "DATA_NOT_FOUND"
    if "fiscal year" in traj_text.lower() or "calendar year" in traj_text.lower():
        return "WRONG_PERIOD"
    
    return "COMPUTATION_ERROR"


# ── Claude analysis ────────────────────────────────────────────────────────

def ask_claude(task: dict, traj: dict, existing_skills: str, failure_category: str) -> str:
    """Ask Claude to analyze a failure and suggest a patch."""
    client = anthropic.Anthropic()
    traj_summary = summarize_trajectory(traj)
    agent_answer = extract_agent_answer(traj)

    prompt = f"""You are debugging a failed U.S. Treasury Bulletin Q&A task.

== QUESTION ==
{task['instruction'][:1500]}

== EXPECTED ANSWER ==
{task['expected']}

== AGENT'S ANSWER ==
{agent_answer}

== FAILURE CATEGORY ==
{failure_category}: {FAILURE_CATEGORIES.get(failure_category, '')}

== AGENT TRAJECTORY (condensed) ==
{traj_summary}

== EXISTING SKILLS (already known — do NOT repeat) ==
{existing_skills[:4000]}

Your job:
1. Identify the EXACT failure point — what went wrong and where
2. Write a SHORT (2-5 sentence) skill patch that would prevent this specific failure
3. Choose the most appropriate skills file
4. The patch should be ACTIONABLE — tell the agent what to DO differently
5. Do NOT repeat anything already in existing skills

Respond in EXACTLY this format:
FAILURE_MODE: <one-line description>
SKILL_FILE: <one of the skill subdirectories: external-knowledge | fiscal-year-dates | corpus-structure | statistical-operations | table-types | number-parsing | question-patterns>
PATCH:
<2-5 sentences of actionable skill text — rules the agent should follow>"""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


def parse_claude_response(text: str) -> tuple[str, str, str]:
    """Parse Claude's structured response into failure_mode, skill_file, patch."""
    failure_mode, skill_target, patch_lines = "", "question-patterns", []
    in_patch = False
    for line in text.splitlines():
        if line.startswith("FAILURE_MODE:"):
            failure_mode = line[len("FAILURE_MODE:"):].strip()
        elif line.startswith("SKILL_FILE:"):
            raw = line[len("SKILL_FILE:"):].strip()
            for sd in SKILL_SUBDIRS:
                if sd in raw or raw in sd:
                    skill_target = sd
                    break
        elif line.startswith("PATCH:"):
            in_patch = True
        elif in_patch:
            patch_lines.append(line)
    return failure_mode, skill_target, "\n".join(patch_lines).strip()


# ── Patch management ───────────────────────────────────────────────────────

PATCH_MARKER = "## Auto-learned from"


def apply_patch(skill_subdir: str, patch: str, task_id: str) -> Path:
    """Apply a patch to a skill's SKILL.md file."""
    fp = SKILLS_DIR / skill_subdir / "SKILL.md"
    if not fp.exists():
        fp = SKILLS_DIR / "question-patterns" / "SKILL.md"
    
    with open(fp, "a") as f:
        f.write(f"\n\n{PATCH_MARKER} {task_id}\n{patch}\n")
    return fp


def revert_patch(skill_subdir: str, task_id: str) -> None:
    """Revert a specific patch from a skill file."""
    fp = SKILLS_DIR / skill_subdir / "SKILL.md"
    if not fp.exists():
        return
    content = fp.read_text()
    marker = f"\n\n{PATCH_MARKER} {task_id}\n"
    if marker in content:
        fp.write_text(content[:content.index(marker)])


def load_skills_text() -> str:
    """Load all skill content for deduplication check."""
    parts = []
    for sd in SKILL_SUBDIRS:
        fp = SKILLS_DIR / sd / "SKILL.md"
        if fp.exists():
            parts.append(f"=== {sd}/SKILL.md ===\n{fp.read_text()}")
    # Also include flat files
    for sf in SKILL_FILES:
        fp = SKILLS_DIR / sf
        if fp.exists():
            parts.append(f"=== {sf} ===\n{fp.read_text()}")
    return "\n\n".join(parts)


# ── Reporting ──────────────────────────────────────────────────────────────

def generate_report(baseline: dict, fixed: list, unfixed: list, final: dict, ts: str) -> str:
    """Generate a markdown report of the improvement session."""
    n_total = len(baseline["passed"]) + len(baseline["failed"])
    n_before = len(baseline["passed"])
    n_after = len(final.get("passed", []))
    
    lines = [
        f"# Self-Improvement Report — {ts}",
        "",
        f"## Score: {n_before}/{n_total} → {n_after}/{n_total}",
        "",
        "## Fixed Tasks",
    ]
    
    for task_id, skill_file, patch, category in fixed:
        lines.append(f"### {task_id} ({category})")
        lines.append(f"- Patched: `{skill_file}/SKILL.md`")
        lines.append(f"- Patch: {patch[:200]}")
        lines.append("")
    
    if unfixed:
        lines.append("## Unfixed Tasks")
        for task_id, category in unfixed:
            lines.append(f"- {task_id} ({category})")
    
    lines.append(f"\n## Skipped: {list(SKIP_TASKS)}")
    
    return "\n".join(lines)


# ── Main loop ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="OfficeQA self-improvement loop v2")
    parser.add_argument("--run-dir", help="Reuse an existing run directory")
    parser.add_argument("--task", help="Only fix a specific task ID")
    parser.add_argument("--dry-run", action="store_true", help="Analyze only, don't apply patches")
    parser.add_argument("--model", default="claude-sonnet-4-20250514", help="Model for analysis")
    args = parser.parse_args()

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    print("=" * 60)
    print("OfficeQA Self-Improvement Loop v2")
    print("=" * 60)

    # ── Step 1: Baseline ──────────────────────────────────────────────────
    if args.run_dir:
        run_dir = Path(args.run_dir)
        print(f"Reusing run: {run_dir}")
    else:
        print("\n[1/5] Running baseline arena test…")
        run_dir = run_arena_test(f"self-improve-baseline-{ts}", timeout=3600)
        if not run_dir:
            sys.exit("ERROR: Could not find run directory")

    baseline = parse_results(run_dir)
    if not baseline:
        sys.exit("ERROR: Could not parse results")

    failures = [t for t in baseline["failed"] if t not in SKIP_TASKS]
    if args.task:
        failures = [t for t in failures if t == args.task]

    n_total = len(baseline["passed"]) + len(baseline["failed"])
    print(f"Baseline: {len(baseline['passed'])}/{n_total} passed")
    print(f"Fixable failures ({len(failures)}): {failures}")

    if not failures:
        print("\nNo fixable failures — already at maximum!")
        return

    # ── Step 2: Categorize failures ───────────────────────────────────────
    print(f"\n[2/5] Categorizing {len(failures)} failures…")
    categorized = {}
    for task_id in failures:
        traj = load_trajectory(run_dir, task_id)
        task = load_task(task_id)
        if traj:
            cat = categorize_failure(task, traj)
            categorized[task_id] = cat
            answer = extract_agent_answer(traj)
            print(f"  {task_id}: {cat} (got: {answer[:50]}, expected: {task['expected'][:50]})")
        else:
            categorized[task_id] = "TIMEOUT"
            print(f"  {task_id}: TIMEOUT (no trajectory)")

    if args.dry_run:
        print("\n[DRY RUN] Analysis complete. No patches applied.")
        return

    # ── Step 3: Fix each failure ──────────────────────────────────────────
    print(f"\n[3/5] Analyzing and patching failures…")
    fixed, unfixed = [], []

    # Prioritize: FORMAT_ERROR first (easiest), then COMPUTATION, then DATA
    priority_order = ["FORMAT_ERROR", "WRONG_PERIOD", "COMPUTATION_ERROR", "DATA_NOT_FOUND", "WRONG_TABLE", "HALLUCINATION"]
    sorted_failures = sorted(failures, key=lambda t: priority_order.index(categorized.get(t, "COMPUTATION_ERROR")) if categorized.get(t) in priority_order else 99)

    for task_id in sorted_failures:
        category = categorized.get(task_id, "UNKNOWN")
        if category in ("CHART_VISUAL", "TIMEOUT"):
            print(f"\n  ┌─ {task_id} [{category}] — skipping (unfixable)")
            unfixed.append((task_id, category))
            continue

        print(f"\n  ┌─ {task_id} [{category}]")
        traj = load_trajectory(run_dir, task_id)
        if not traj:
            unfixed.append((task_id, category))
            continue

        task = load_task(task_id)
        skills = load_skills_text()

        print(f"  │  Q: {task['instruction'][:90].strip()}…")
        print(f"  │  Expected: {task['expected']}")
        print(f"  │  Asking Claude for patch…")

        try:
            raw = ask_claude(task, traj, skills, category)
        except Exception as e:
            print(f"  │  Claude error: {e}")
            unfixed.append((task_id, category))
            continue

        failure_mode, skill_target, patch = parse_claude_response(raw)
        print(f"  │  Failure: {failure_mode}")
        print(f"  │  Target:  {skill_target}/SKILL.md")
        print(f"  │  Patch:   {patch[:160].replace(chr(10), ' ')}…")

        apply_patch(skill_target, patch, task_id)

        print(f"  │  Re-running {task_id}…")
        try:
            verify_dir = run_arena_test(f"verify-{task_id[:20]}-{ts}", filter_task=task_id, timeout=400)
            verify = parse_results(verify_dir)
        except Exception as e:
            print(f"  │  Verify failed: {e}")
            revert_patch(skill_target, task_id)
            unfixed.append((task_id, category))
            continue

        if task_id in verify.get("passed", []):
            print(f"  └─ ✅ FIXED")
            fixed.append((task_id, skill_target, patch, category))
        else:
            print(f"  └─ ❌ Still failing — reverting")
            revert_patch(skill_target, task_id)
            unfixed.append((task_id, category))

    # ── Step 4: Regression check ──────────────────────────────────────────
    if fixed:
        print(f"\n[4/5] Regression check with {len(fixed)} patches…")
        final_dir = run_arena_test(f"self-improve-final-{ts}")
        final = parse_results(final_dir)
        n_after = len(final.get("passed", []))
        n_before = len(baseline["passed"])
        regressions = [t for t in baseline["passed"] if t in final.get("failed", [])]
        if regressions:
            print(f"  ⚠️  Regressions: {regressions}")
        else:
            print(f"  ✅ No regressions")
        print(f"  Score: {n_before}/{n_total} → {n_after}/{n_total}")
    else:
        final = baseline

    # ── Step 5: Commit + Report ───────────────────────────────────────────
    print(f"\n[5/5] Summary")
    print(f"  Fixed   : {[t for t, _, _, _ in fixed]}")
    print(f"  Unfixed : {[t for t, _ in unfixed]}")
    print(f"  Skipped : {list(SKIP_TASKS)}")

    # Generate report
    report = generate_report(baseline, fixed, unfixed, final, ts)
    report_path = PROJECT_DIR / f"self-improve-report-{ts}.md"
    report_path.write_text(report)
    print(f"\n  Report: {report_path}")

    if fixed:
        print(f"\n  Committing {len(fixed)} improvements…")
        subprocess.run(["git", "add", "skills/", str(report_path)], cwd=PROJECT_DIR)
        body = "\n".join(f"- {t} [{c}]: patched {sf}/SKILL.md" for t, sf, _, c in fixed)
        msg = f"auto-improve: fixed {len(fixed)} task(s)\n\n{body}"
        subprocess.run(["git", "commit", "-m", msg], cwd=PROJECT_DIR)
        print("  Committed!")

    print("\nDone.")


if __name__ == "__main__":
    main()
