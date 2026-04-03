# Proposal: Recursive Language Models (RLMs) for OfficeQA

**Date:** 2026-04-02
**Author:** Research assessment
**Status:** Proposed
**References:** [Zhang & Khattab, arXiv:2512.24601](https://arxiv.org/abs/2512.24601), [Prime Intellect RLM blog](https://www.primeintellect.ai/blog/rlm), [Minimal implementation](https://github.com/alexzhang13/rlm-minimal)

---

## 1. Background: What Are Recursive Language Models?

Recursive Language Models (RLMs) are an inference paradigm introduced by Alex Zhang and Omar Khattab (MIT SAIL, December 2025) that allows LLMs to process arbitrarily long prompts by treating the context as part of an external environment rather than stuffing it into the context window.

### Core Mechanism

Instead of a standard `llm.completion(query, context)` call, an RLM:

1. Receives only the **query** — the (potentially huge) context is stored as a variable in a persistent **Python REPL environment**
2. The root LLM writes Python code to **programmatically inspect, grep, slice, and transform** the context
3. The root LLM can **spawn recursive sub-LLM calls** over subsets of the context (depth=1 in the paper's experiments)
4. The root LLM **aggregates** sub-LLM results and builds up a final answer iteratively

The key insight: the root LLM's context window is never clogged with the full input. It grows slowly because the LLM only sees REPL outputs (truncated to ~8K chars per turn), not the raw context.

### Key Results from the Paper

| Benchmark | Comparison | Result |
|-----------|-----------|--------|
| OOLONG (132K tokens) | RLM(GPT-5-mini) vs GPT-5 | +34 points (~114% increase) |
| OOLONG (263K tokens) | RLM(GPT-5-mini) vs GPT-5 | +15 points (~49% increase) |
| BrowseComp-Plus (1000 docs, ~10M+ tokens) | RLM(GPT-5) vs GPT-5 | 100% vs ~60% accuracy |

RLM(GPT-5-mini) outperformed vanilla GPT-5 at roughly the same API cost per query. Performance did not degrade at 10M+ token scale.

### Emergent Strategies Observed

The RLM root LLM spontaneously develops these patterns:

- **Peeking:** Reads first N characters to understand structure
- **Grepping:** Uses regex/keyword search to narrow the search space
- **Partition + Map:** Chunks context, dispatches sub-LLM calls per chunk, aggregates results
- **Summarization:** Sub-LLMs summarize chunks; root LLM reasons over summaries
- **Programmatic processing:** For deterministic tasks (diff tracking, counting), writes code instead of reasoning

### Prime Intellect Validation (January 2026)

Prime Intellect independently validated RLMs across 4 environments with GPT-5-mini, GLM 4.6, and INTELLECT-3. Key findings:

- RLM improves performance on long-context tasks (Oolong, DeepDive) and token-intensive tool use
- RLM hurts performance on math-only tasks where the standard Python tool suffices (overhead without benefit)
- Environment-specific tips significantly improve RLM performance (evidence that training/prompting for RLM usage matters)
- Sub-LLMs dramatically compress the main model's context window while scaling total thinking tokens

---

## 2. Current Harness Already Has RLM DNA

The openhands-sdk agent already implements ~60-70% of the RLM pattern:

| RLM Component | Current Harness Equivalent | Gap |
|--------------|---------------------------|-----|
| Context as environment variable | Corpus lives on disk (`/app/corpus/*.txt`), not in prompt | ✅ Already done |
| Programmatic context navigation | Agent uses `grep -n`, `awk`, bash loops, Python scripts | ✅ Already done |
| Root LLM never sees full context | Prompt says "NEVER read entire bulletin files" | ✅ Already done |
| Persistent REPL environment | Docker container with bash + Python execution | ✅ Already done |
| Iterative answer refinement | Agent writes preliminary answer, updates as it refines | ✅ Already done |
| **Recursive sub-LLM calls** | **Not implemented** | ❌ Missing |
| **Parallel sub-LLM dispatch** | **Not implemented** | ❌ Missing |

The missing piece is the "recursive" part — the ability for the root agent to spawn fresh sub-LLM calls over extracted context chunks for semantic understanding, verification, or parallel processing.

---

## 3. Feasibility Assessment

### 3.1 What's Available Inside the Container

From the openhands-sdk v1.16.0 agent logs (run-62221e), the agent has these tools:

**Built-in tools:**
- `terminal` — bash execution (the agent runs `grep`, `awk`, Python scripts, etc.)
- `file_editor` — create/edit files in the container
- `task_tracker` — task management
- `FinishTool` — signal task completion
- `ThinkTool` — internal reasoning (no tool call)

**MCP tools (27 total):**
- `mcpcalc_*` (10 tools) — calculators, CAS sessions, spreadsheet sessions
- `math-learning_*` (17 tools) — arithmetic, statistics, matrices, plotting

**No built-in LLM calling tool.** The openhands-sdk harness does NOT provide a way for the agent to spawn sub-LLM calls. There is no `llm_call`, `sub_agent`, or `ask_model` tool. The harness manages the single LLM loop externally — the agent can only interact with the environment via the tools listed above.

**However**, the container does have network access (it connects to remote MCP servers over HTTPS) and has `OPENROUTER_API_KEY` / `LLM_API_KEY` available as environment variables (passed through `arena.yaml` env block). This means the agent can make HTTP requests to the OpenRouter API from within bash or Python scripts using stdlib `urllib.request` — no `openai` package needed, no `pip` needed, no harness changes needed.

### 3.2 Why We Don't Need the `openai` Package

The `openai` package is a convenience wrapper around HTTP calls. The OpenRouter API is OpenAI-compatible, so a sub-LLM call is just a POST request to `https://openrouter.ai/api/v1/chat/completions` with a JSON body. Python's `urllib.request` (stdlib, always available) handles this fine. The helper script in Approach B uses only stdlib.

### 3.3 No Harness Changes Required

This is implementable entirely through prompt changes + a Python helper script that the agent writes to disk via `file_editor` or `echo` at the start of each task. The harness, `arena.yaml`, and MCP configuration remain untouched. The agent simply uses its existing `terminal` tool to run `python3 /app/sub_llm.py "question" /tmp/chunk.txt` — the same way it already runs Python computation scripts.

### 3.4 Constraints

| Constraint | Impact | Mitigation |
|-----------|--------|------------|
| **Iteration budget** | Agent already exhausts budget on complex questions (4/9 failures in run-cb4f99). Each sub-LLM call consumes 1 agent turn (write chunk to file + run script in one bash command). | Limit sub-LLM usage to verification only, not primary extraction. |
| **600s timeout per task** | Sub-LLM API calls add latency (~2-5s each via OpenRouter). | Cap at 2-3 sub-LLM calls per task. Use only for high-value verification. |
| **Cost per task** | Current: $0.02-$0.22/task. Sub-LLM calls add ~$0.01-0.03 each. | Modest increase. At 246 questions × 3 calls = ~$7-22 additional. Acceptable. |
| **Harness controls outer loop** | Can't replace openhands-sdk with a true RLM scaffold. Agent must work within the harness's tool-call iteration model. | Implement RLM pattern within the existing agent loop via prompt instructions + helper scripts. |
| **Model capability** | minimax-m2.5 may not follow complex RLM instructions as reliably as GPT-5-mini (which the paper used). | Keep instructions simple. Use sub-LLM for narrow, well-defined tasks only. |
| **Network reliability** | Sub-LLM calls depend on OpenRouter API availability from within the container. | Helper script has timeout + error handling. Agent falls back to its own judgment if the call fails. |

### 3.5 Verdict

**Yes, RLM can be partially implemented within the current harness, with zero harness changes.** The openhands-sdk does NOT provide a built-in sub-LLM tool, but the agent has network access and API keys in the environment. A stdlib-only Python script called via the existing `terminal` tool can hit the OpenRouter API directly. No new dependencies, no `pip`, no `openai` package, no `arena.yaml` changes. The full RLM scaffold (REPL notebook with recursive `rlm.completion()` calls) would require harness-level changes not feasible before the April 4 deadline, but the core value proposition — sub-LLM calls for verification and semantic disambiguation — is achievable today.

---

## 4. Implementation Approaches

### Approach A: Prompt-Level RLM (Low Effort, Low-Medium Impact)

**What:** Encode the RLM reasoning pattern in the prompt without actual sub-LLM calls. Formalize the "context as environment variable" mindset more explicitly.

**Changes:**
- Restructure the execution workflow to match RLM stages: Peek → Narrow → Process → Aggregate
- Make the "programmatic navigation" pattern more explicit (the agent already does this, but inconsistently)

**Impact:** Marginal. The current prompt already captures most of this. The failures in run-cb4f99 aren't caused by lack of programmatic navigation — they're caused by wrong table selection, formula errors, and iteration budget exhaustion.

**Effort:** ~1 hour (prompt edits only)

### Approach B: Sub-LLM via curl/urllib (Medium Effort, High Impact) ⭐ RECOMMENDED

**What:** Add a Python helper script that the agent copies into the container and uses to spawn sub-LLM calls for verification and disambiguation.

**Changes:**

1. **Helper script** (`sub_llm.py`) using only stdlib:

```python
#!/usr/bin/env python3
"""Sub-LLM helper for RLM-style verification. Uses only stdlib (no pip)."""
import json, urllib.request, os, sys

def sub_query(query, context_chunk, model="minimax/minimax-m2.5", max_tokens=500):
    """Spawn a sub-LLM call over a context chunk. Returns the response text."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY', os.environ.get('LLM_API_KEY', ''))}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://arena.sentient.xyz",
    }
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "Answer precisely using ONLY the provided context. Be concise."},
            {"role": "user", "content": f"Context:\n{context_chunk}\n\nQuestion: {query}"}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }).encode()
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"ERROR: {e}"

if __name__ == "__main__":
    # CLI usage: python3 sub_llm.py "question" /path/to/chunk.txt
    if len(sys.argv) >= 3:
        question = sys.argv[1]
        with open(sys.argv[2]) as f:
            chunk = f.read()
        print(sub_query(question, chunk))
```

2. **Prompt additions** — new section in `officeqa_prompt.j2`:

```
### Sub-LLM Verification (for ambiguous extractions)

You have a helper script at `/app/sub_llm.py` for spawning independent verification queries.
Use it ONLY for these specific cases (max 2-3 calls per task):

1. **Table identity verification:** After extracting values, save 30 lines of context
   around the extraction to `/tmp/chunk.txt`, then:
   python3 /app/sub_llm.py "What table is this? What is the value for [ROW_LABEL]?" /tmp/chunk.txt

2. **Formula disambiguation:** When unsure which formula to apply:
   python3 /app/sub_llm.py "The question asks for '[EXACT PHRASE]'. Should I use
   percent change (B-A)/A or symmetric percent difference |A-B|/avg?" /tmp/chunk.txt

3. **Self-consistency check replacement:** Instead of re-grepping with a different
   pattern, ask a sub-LLM to independently extract the value from the same chunk.

Do NOT use sub-LLM for primary data extraction — use grep/awk for that.
Do NOT use more than 3 sub-LLM calls per task — each costs iteration budget.
```

3. **Prompt modification** — agent copies `sub_llm.py` as first action:

Add to the execution workflow step 3 (before search):
```
echo '<contents of sub_llm.py>' > /app/sub_llm.py
```

Or inline it into the prompt's compute.py block so it's copied alongside the calculation library.

**Failure modes addressed:**

| Failure | How Sub-LLM Helps |
|---------|-------------------|
| uid0097 (ESF capital interpretation) | Sub-LLM independently reads the table chunk and answers "What is total nominal capital?" — catches the Capital Account vs Total Capital confusion |
| uid0127 (duplicate data extraction) | Sub-LLM independently extracts values from the chunk, catching copy/paste errors |
| uid0220 (formula flip) | Sub-LLM asked "which formula for 'percent difference'?" provides independent confirmation before the agent second-guesses itself |
| uid0246 (wrong table for T-bills) | Sub-LLM verifies table identity from the chunk header |

**Failure modes NOT addressed (or worsened):**

| Failure | Risk |
|---------|------|
| uid0194, uid0004, uid0136 (no answer.txt — budget exhaustion) | Sub-LLM calls consume 2-3 turns each. Could worsen budget pressure. Mitigation: only use for verification AFTER preliminary answer is written. |
| uid0030 (chart question) | Sub-LLM can't see charts either. No help. |
| uid0023 (Finish without write) | Unrelated to RLM. Already fixed by early-write rule. |

**Effort:** ~3-4 hours (helper script + prompt edits + smoke test)

**Expected impact:** +10-15% by fixing 2-3 of the wrong-table/wrong-formula failures. Risk of -5% if sub-LLM calls push borderline tasks over the iteration budget.

### Approach C: Full RLM Harness (High Effort, Highest Impact, Post-Competition)

**What:** Replace the openhands-sdk harness with a custom RLM harness where the root LLM operates in a Jupyter-like REPL environment with native recursive sub-LLM calls.

**Changes:**
- Fork the arena agent framework
- Implement `RLM_REPL` class following [rlm-minimal](https://github.com/alexzhang13/rlm-minimal) architecture
- Root LLM gets only the question + awareness that corpus exists as a variable
- Sub-LLM calls are first-class functions in the REPL (`rlm_call(query, chunk)`)
- Answer built up in an `answer` variable with `answer["ready"]` flag (Prime Intellect pattern)
- Parallel sub-LLM dispatch via `llm_batch()` for multi-year extraction

**Architecture:**

```
┌─────────────────────────────────────────────────────────┐
│                    RLM Root LLM                          │
│  - Receives: question only                               │
│  - Environment: Python REPL with corpus as variable      │
│  - Can call: rlm_call(query, chunk), llm_batch(prompts)  │
│  - Answer: answer["content"] / answer["ready"]           │
└──────────────────────┬──────────────────────────────────┘
                       │ Python code execution
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    REPL Environment                       │
│  corpus = open("/app/corpus/index.txt").read()            │
│  files = glob("/app/corpus/*.txt")                        │
│                                                           │
│  # Root LLM writes code like:                             │
│  matches = grep("Total assets", files)                    │
│  chunk = read_lines(matches[0].file, start-10, start+20)  │
│  result = rlm_call("What is total capital?", chunk)       │
│  answer["content"] = result                               │
│  answer["ready"] = True                                   │
└─────────────────────────────────────────────────────────┘
                       │ sub-LLM calls
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Sub-LLM (depth=1, fresh context)             │
│  - Receives: sub-query + chunk only                       │
│  - No REPL, no recursion                                  │
│  - Returns: concise answer string                         │
└─────────────────────────────────────────────────────────┘
```

**Why this is the ideal long-term approach:**
- Root LLM context stays lean regardless of corpus size (697 files, ~10M+ tokens total)
- Sub-LLMs handle semantic extraction with fresh context (no rot from prior turns)
- Parallel dispatch (`llm_batch`) enables extracting multi-year time series in one round
- The agent naturally learns to peek → narrow → delegate → aggregate
- Compatible with future RL training on the RLM scaffold (Prime Intellect's roadmap)

**Effort:** ~2-3 weeks (harness development + testing + tuning)

**Expected impact:** +20-30% by fundamentally changing how the agent navigates the corpus. Eliminates context rot, enables parallel extraction, and provides fresh-context verification for free.

---

## 5. Recommendation

| Timeframe | Approach | Effort | Expected Impact |
|-----------|----------|--------|-----------------|
| **Now (before April 4)** | **Approach B: Sub-LLM via urllib** | 3-4 hours | +10-15% |
| Post-competition | Approach C: Full RLM harness | 2-3 weeks | +20-30% |

**Immediate action:** Implement Approach B. Add `sub_llm.py` helper and prompt instructions for sub-LLM verification. Limit to 2-3 calls per task, used only after the preliminary answer is written (to avoid worsening the budget exhaustion failure mode).

**Key risk:** minimax-m2.5 may not reliably follow the "use sub-LLM for verification" instructions. The Prime Intellect results showed that environment-specific tips matter a lot — models without tips often misuse the RLM scaffold. A smoke test on 3-5 tasks is essential before a full run.

**Post-competition:** Approach C is the real prize. The OfficeQA corpus (697 files, heterogeneous tables, multi-document dependencies) is exactly the kind of task where RLMs shine — long context, semantic extraction, multi-hop reasoning. A proper RLM harness with parallel sub-LLM dispatch could handle the entire corpus as a single "context variable" without any retrieval infrastructure.

---

## 6. Open Questions

1. **Model choice for sub-LLM:** Should the sub-LLM be the same model (minimax-m2.5) or a cheaper/faster one? The paper used GPT-5-mini for both root and sub-LLM. A smaller model for sub-queries could reduce cost and latency.

2. **Depth > 1:** The paper only tested depth=1 (root → sub-LLM, no further recursion). For OfficeQA, depth=1 should suffice — the agent extracts a chunk and asks a sub-LLM to interpret it. Deeper recursion adds complexity without clear benefit for this task.

3. **Parallel dispatch:** The biggest win from RLMs on multi-year time series questions would be parallel sub-LLM calls (e.g., "extract the value for each of these 12 months" dispatched simultaneously). This requires `llm_batch()` which is only feasible in Approach C.

4. **Training for RLM usage:** Both the paper and Prime Intellect emphasize that models not trained for RLM usage underperform. minimax-m2.5 has never seen RLM-style prompts. The post-trained RLM-Qwen3-8B outperformed base Qwen3-8B by 28.3% — suggesting that fine-tuning for RLM usage is a significant multiplier. This is a post-competition consideration.

5. **Interaction with existing MCP tools:** The current mcpcalc and math-learning MCP servers handle computation. In a full RLM harness (Approach C), these could be given to sub-LLMs only (Prime Intellect's design), keeping the root LLM's context free of verbose tool outputs. This is a natural fit.
