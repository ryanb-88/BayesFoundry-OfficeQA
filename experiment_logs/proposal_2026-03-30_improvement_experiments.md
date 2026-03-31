# Proposal: Experiment Plan to Improve from 38.6% → 70%+

**Date:** 2026-03-30
**Author:** Kiro + Ryan
**Status:** Proposed
**Baseline:** 38.6% on full 246-question benchmark (competition submission)
**Local best:** 100% on 10/20 local samples with `z-ai/glm-5`

## Diagnosis: Why 38.6%?

The 38.6% score on the full 246-question benchmark vs 100% on 10 local samples reveals a severe overfitting problem. Our prompt, skills, and MCP tools were tuned for a narrow slice of question types (ESF balance sheets, a single visual chart, a few specific calculations). The full benchmark has 246 questions spanning dozens of table types, document eras (1939-2025), calculation methods, and answer formats that our current system has never seen.

The root causes break down into three layers:

1. **Corpus representation quality** — The TXT corpus is a lossy conversion from PDFs. Tables with merged cells, multi-line headers, footnotes, and complex layouts are mangled into pipe-delimited text. The agent can't extract what isn't faithfully represented.

2. **Model capability ceiling** — `z-ai/glm-5` via OpenRouter is a mid-tier model. It struggles with complex multi-step reasoning, long-context extraction across 12+ files, and precise numerical computation. It also never invokes MCP tools, limiting us to bash/grep/read workflows.

3. **Prompt/skill overfitting** — The prompt is heavily ESF-focused with worked examples that only cover ~5 question patterns. 60% of the benchmark hits patterns we've never tested.

## Experiment Ranking (Highest → Lowest Expected Impact)

---

### Experiment 1: Upgrade Corpus with Higher-Fidelity PDF Parsing
**Expected impact: +15-25% absolute**
**Effort: Medium-High**
**Risk: Low**

#### Hypothesis
The current TXT corpus is a pre-parsed, lossy representation of the original Treasury Bulletin PDFs. Tables with merged cells, multi-line headers, footnotes, and complex layouts lose structural fidelity in the pipe-delimited text conversion. Many wrong answers likely stem from the agent extracting garbled or misaligned values from poorly-parsed tables.

Databricks' recent `ai_parse_document` work (and the broader document intelligence space) demonstrates that modern parsing systems preserve table structure, bounding boxes, and spatial relationships far better than simple text extraction. The OfficeQA benchmark itself was created by Databricks, and their parsing system achieves state-of-the-art quality on document understanding tasks.

#### Design

**Option A: Re-parse from original PDFs using a high-quality parser**
- The OfficeQA repo provides raw PDFs at `treasury_bulletin_pdfs/` and parsed JSONs at `treasury_bulletins_parsed/jsons/`
- Use a state-of-the-art document parser (Docling, Marker, or Unstructured.io) to re-parse the PDFs into structured JSON with:
  - Preserved table structure (row/column spans, headers, units)
  - Figure/chart detection with bounding boxes
  - Section hierarchy preservation
  - Footnote association with their parent tables
- Convert the structured JSON into an improved TXT format that the agent can grep/read
- Key improvement: tables should include explicit column headers on every row (not just the first), units in a metadata line, and footnotes inline

**Option B: Use the existing parsed JSONs as a supplementary corpus**
- The Docker image may already contain `treasury_bulletins_parsed/jsons/` with richer structure
- Build a pre-processing step that converts these JSONs into agent-friendly format
- Lower effort than re-parsing from PDFs, but quality depends on the existing parse

**Option C: Hybrid — use TXT for text search, fall back to JSON for table extraction**
- Keep the current TXT corpus for grep-based search (fast, works well for finding sections)
- When the agent needs to extract a specific table value, use a Python script that reads the structured JSON version for that bulletin and returns the precise cell value
- This could be implemented as an MCP tool or a bash-callable Python script

#### Metrics
- Run the full 20-sample local benchmark before and after corpus upgrade
- Focus on tasks that require precise table value extraction (uid0057, uid0217, uid0241)
- Measure: accuracy delta, number of "wrong value extracted" errors

#### Why highest priority
Every downstream improvement (better prompts, better models, better tools) is bottlenecked by corpus quality. If the agent can't find the right number in the text, no amount of reasoning will fix it. This is the foundation layer.

---

### Experiment 2: Model Upgrade — Switch to a Stronger Reasoning Model
**Expected impact: +10-20% absolute**
**Effort: Low**
**Risk: Medium (cost increase)**

#### Hypothesis
`z-ai/glm-5` is a capable model but has clear limitations:
- Never invokes MCP tools (only uses bash/grep/read/write)
- Struggles with multi-step calculations (HP filter, Euclidean norm, geometric mean)
- Token exhaustion on multi-file tasks (uid0057: 514K input tokens, 0 output tokens)
- Stochastic variance of 40-80% on hard tasks

A stronger model (e.g., Claude Sonnet 4, GPT-4.1, or Gemini 2.5 Pro) would likely:
- Follow complex prompt instructions more reliably
- Perform multi-step math with fewer errors
- Potentially use MCP tools if instructed
- Handle longer contexts without exhaustion

#### Design

| Experiment | Model | Expected Strength | Cost/Task |
|-----------|-------|-------------------|-----------|
| 2a | `anthropic/claude-sonnet-4` | Strong reasoning, tool use, long context | ~$0.30 |
| 2b | `google/gemini-2.5-pro` | Very long context (1M), strong math | ~$0.15 |
| 2c | `openai/gpt-4.1` | Strong instruction following, tool use | ~$0.25 |
| 2d | `deepseek/deepseek-r1` | Strong math/reasoning, low cost | ~$0.10 |
| 2e | `z-ai/glm-5` (baseline) | Current best local | ~$0.24 |

**Protocol:**
1. Run each model on the same 10-task local benchmark (the tasks from the 100% run)
2. Compare: accuracy, latency, cost, MCP tool usage, failure modes
3. Pick the best performer and run on the full 20-task local set
4. If a model uses MCP tools, the existing MCP server becomes valuable rather than dead weight

#### Why high priority
Model capability is the second biggest lever after corpus quality. A model that can reliably follow instructions, use tools, and do math correctly will benefit from every other improvement we make.

---

### Experiment 3: Pre-Computed Answer Index for Common Patterns
**Expected impact: +8-15% absolute**
**Effort: Medium**
**Risk: Low**

#### Hypothesis
Many benchmark questions follow predictable patterns that can be partially pre-computed. Instead of having the agent search, extract, and compute from scratch every time, we can build a structured index that maps common query patterns to pre-extracted data.

#### Design

**3a: Table-of-Contents Index**
Build a comprehensive index file (`/app/corpus/table_index.json`) that maps:
```json
{
  "treasury_bulletin_1989_06.txt": {
    "tables": [
      {"id": "ESF-1", "title": "Exchange Stabilization Fund", "line_start": 1234, "line_end": 1290, "dates_covered": ["Dec 31, 1988", "Mar 31, 1989"], "units": "thousands"},
      {"id": "FD-1", "title": "Summary of Federal Debt", "line_start": 456, "line_end": 520, "dates_covered": ["1989"], "units": "millions"}
    ]
  }
}
```
This eliminates the agent's most expensive operation: searching for the right table in the right file.

**3b: Pre-Extracted Key Values**
For the most commonly queried data points (ESF total assets, total capital, gross federal debt, T-bill rates), pre-extract a time series:
```json
{
  "esf_total_assets": {
    "1989-03-31": 26346918000,
    "1989-06-30": 27123456000,
    ...
  }
}
```
The agent can look up values directly instead of parsing tables.

**3c: Computation Templates**
Pre-build Python scripts for common calculations that the agent can invoke:
```python
# /app/tools/compute.py
def geometric_mean(values): ...
def theil_index(values): ...
def annualized_volatility(returns): ...
def cagr(start, end, years): ...
def euclidean_norm(values): ...
def hp_filter(series, lamb=1600): ...
```
The agent calls `python3 /app/tools/compute.py geometric_mean 1.05 1.03 1.07` instead of writing computation code from scratch.

#### Why medium-high priority
This directly addresses the token exhaustion problem (Gap 4) and computation errors (Gap 3). Pre-computed data means fewer tool calls, less context consumed, and more reliable answers.

---

### Experiment 4: Prompt Generalization — Remove ESF Bias, Add Diverse Worked Examples
**Expected impact: +5-10% absolute**
**Effort: Medium**
**Risk: Low**

#### Hypothesis
The current prompt is ~3,500 lines, heavily biased toward ESF balance sheet questions. Of the 246 benchmark questions, ESF questions are likely <20%. The prompt's worked examples, verification checklist, and terminology guide all assume ESF context. Questions about T-bill rates, federal expenditures, capital movements, public debt, and other topics get minimal guidance.

#### Design

**4a: Add 5-6 diverse worked examples covering untested question types:**
- T-bill rate lookup (date answer format)
- Gross federal debt across 12 years (multi-file extraction)
- Geometric mean of discount rates (complex calculation)
- Federal expenditures comparison (pre-1940s document)
- Public debt outstanding mean (simple aggregation)
- Annualized volatility (Brownian motion model)

**4b: Generalize the verification checklist:**
Current checklist is ESF-specific ("Did you multiply by 1,000?"). Add:
- Check if the table header specifies units (millions, billions, thousands, percent)
- Check if the question asks for a date, percentage, or text answer
- Check if the answer should be in brackets, comma-separated, or plain
- Check if the question specifies a rounding rule

**4c: Reduce prompt size by removing redundant ESF guidance:**
The prompt repeats ESF unit conversion warnings 5+ times. Consolidate into a single, prominent section. This frees up context window for the agent's actual work.

**4d: Add a "question classification" step at the top of the strategy:**
Before searching for data, have the agent classify the question type:
- Single value lookup → grep + read
- Multi-year time series → bash loop + Python
- Calculation (mean, CAGR, volatility, etc.) → extract data + Python script
- Visual/chart question → chart registry lookup
- Date/text answer → different formatting rules

#### Why medium priority
This is a prompt-only change with no infrastructure cost. It won't fix corpus quality or model capability issues, but it will help the agent handle the 80% of questions it's never seen before.

---

### Experiment 5: Agentic RAG — Add Vector Search for Document Retrieval
**Expected impact: +5-10% absolute**
**Effort: High**
**Risk: Medium**

#### Hypothesis
The agent currently uses grep to find relevant sections, which works well for known patterns but fails when:
- The question uses different terminology than the table headers
- The relevant data is in an unexpected section
- Multiple tables across different bulletins need to be cross-referenced

A vector search index over the corpus would enable semantic retrieval — finding relevant sections even when exact keyword matches fail.

#### Design

**5a: Build a FAISS/ChromaDB index at Docker build time:**
- Chunk each bulletin into sections (~100-200 lines each)
- Embed with a small model (e.g., `all-MiniLM-L6-v2`)
- Store the index at `/app/corpus/vector_index/`
- Add a Python script or MCP tool: `search_corpus(query, top_k=5)` → returns relevant chunks

**5b: Hybrid retrieval:**
- First: vector search to find candidate files/sections
- Then: grep within those sections for precise values
- This combines semantic understanding with exact matching

**5c: Pre-compute embeddings for all table headers and section titles:**
- Lighter weight than full-text embedding
- Maps question keywords to the right table/section quickly

#### Why medium priority
This addresses the "finding the right data" problem but requires significant infrastructure work (embedding model in Docker, index building, retrieval pipeline). The payoff is uncertain — grep already works well for many question types.

---

### Experiment 6: Ensemble / Self-Consistency — Run Multiple Attempts
**Expected impact: +3-8% absolute**
**Effort: Low**
**Risk: Low (cost increase)**

#### Hypothesis
Given the 40-80% stochastic variance on hard tasks, running the same question 2-3 times and taking the majority answer (or the answer that appears most consistent) would smooth out variance.

#### Design

**6a: Within-run self-consistency:**
Add to the prompt: "After computing your answer, re-derive it using a different method. If the two answers disagree, investigate the discrepancy before writing the final answer."

**6b: Multi-run ensemble (if competition allows):**
Submit 3 runs, take the majority answer per question. This is only viable if the competition scoring allows it.

**6c: Confidence-based retry:**
Add to the prompt: "If you are less than 90% confident in your answer, state your confidence level and the main source of uncertainty." Then use a post-processing step to flag low-confidence answers for retry.

#### Why lower priority
This is a variance reduction technique, not a capability improvement. It helps on questions the agent can sometimes solve but doesn't help on questions it fundamentally can't answer.

---

### Experiment 7: Custom Docker Image with Pre-Installed Dependencies
**Expected impact: +2-5% absolute**
**Effort: Low**
**Risk: Low**

#### Hypothesis
The agent sometimes needs Python libraries (statsmodels for HP filter, numpy for linear algebra) that aren't pre-installed in the Docker environment. Installing them at runtime wastes 30-60s of the 600s timeout and sometimes fails.

#### Design
- Build a custom Docker image extending the corpus image
- Pre-install: `numpy`, `scipy`, `statsmodels`, `pandas`
- Pre-build the table index (Experiment 3a) and computation scripts (Experiment 3c)
- Pre-build the vector search index (Experiment 5a) if pursuing that path

#### Why lower priority
This is a reliability improvement, not a capability improvement. It saves time and prevents installation failures but doesn't help the agent find or reason about data it couldn't before.

---

## Recommended Execution Order


### Phase 1: Quick Wins (1-2 days)
| # | Experiment | Effort | Expected Δ |
|---|-----------|--------|------------|
| 1 | Exp 2: Model upgrade A/B test (5 models × 10 tasks) | Low | +10-20% |
| 2 | Exp 4: Prompt generalization (diverse examples, reduce ESF bias) | Medium | +5-10% |
| 3 | Exp 7: Custom Docker image with pre-installed deps | Low | +2-5% |

### Phase 2: Infrastructure (2-3 days)
| # | Experiment | Effort | Expected Δ |
|---|-----------|--------|------------|
| 4 | Exp 1: Corpus upgrade (re-parse or use JSON fallback) | Medium-High | +15-25% |
| 5 | Exp 3: Pre-computed answer index + computation templates | Medium | +8-15% |

### Phase 3: Advanced (3-5 days)
| # | Experiment | Effort | Expected Δ |
|---|-----------|--------|------------|
| 6 | Exp 5: Vector search for semantic retrieval | High | +5-10% |
| 7 | Exp 6: Self-consistency / ensemble | Low | +3-8% |

## Success Criteria

| Target | Score | What It Takes |
|--------|-------|---------------|
| Minimum viable | 50% | Model upgrade + prompt generalization |
| Competitive | 65% | + Corpus upgrade + pre-computed index |
| Top tier | 75%+ | + Vector search + ensemble + custom Docker |

## Constraints

- **Deadline:** April 4th, 2026 (5 days remaining)
- **Budget:** OpenRouter API costs (~$2-5 per full 20-task local run)
- **Infrastructure:** Docker-based, 4GB memory, 600s timeout per task
- **Harness:** OpenCode (opencode-ai CLI) — agent uses bash/grep/read/write tools
- **Competition rules:** Must use the provided corpus Docker image as base

## Appendix: Databricks Document Intelligence Reference

The Databricks blog post on `ai_parse_document` (referenced in this proposal) describes a state-of-the-art document parsing system that:
- Preserves table structure including merged cells and nested structures
- Generates AI captions for figures and diagrams
- Provides spatial metadata and bounding boxes
- Achieves highest quality-per-cost on both OmniOCR and internal benchmarks

This is relevant because the OfficeQA benchmark was created by Databricks, and the quality gap between our current TXT corpus and what modern parsers can produce is likely a significant contributor to our 38.6% score. Experiment 1 directly addresses this by upgrading corpus fidelity.

Key insight from the blog: "Existing parsing tools stop at text extraction. They miss the layouts, visual elements, and relationships that carry meaning in real documents." This exactly describes our current TXT corpus limitation.

Source: [Databricks Blog — PDFs to Production](https://www.databricks.com/blog/pdfs-production-announcing-state-art-document-intelligence-databricks)
