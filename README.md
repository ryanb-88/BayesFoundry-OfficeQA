# BayesFoundry - OfficeQA

**Arena Competition Entry for Grounded Reasoning Challenge**

Team: Ryan Bok, Shradha Agrawal, Gloria H

## Overview

This repository contains our submission for the [Sentient Arena](https://arena.sentient.xyz) OfficeQA campaign — a grounded reasoning competition requiring agents to answer financial questions based on U.S. Treasury Bulletin documents (1939-2025).

## Problem Statement

The OfficeQA benchmark evaluates end-to-end reasoning over long, heterogeneous enterprise documents containing:
- Dense financial tables
- Numerical data
- Multi-document dependencies

Recent results show that performance is limited not only by the language model but by the interaction between document parsing, representation, retrieval, and reasoning strategies.

## Our Approach: LLM-Guided Bayesian Optimization

We frame the design of an end-to-end RAG agent as a **black-box optimization problem**, using Bayesian optimization (BO) to search over pipeline configurations while leveraging an LLM as a prior to guide the search.

### Pipeline Configuration Space

We parameterize the system as:

```
x = (p, r, c, s)
```

Where:
- **p**: Parsing and representation choices (OCR vs. structured parsers)
- **r**: Retrieval parameters (dense, lexical, or hybrid search)
- **c**: Chunking and indexing strategies (page, section, or table-based)
- **s**: Reasoning or skill-composition options

### Key Innovation

Using an LLM as a prior knowledge source that encodes heuristics about document QA systems:
- LLM proposes plausible pipeline configurations based on benchmark corpus description
- Shapes the prior mean and provides high-quality warm-start configurations
- Reflects expert-level design heuristics (e.g., structured parsing for table-heavy PDFs)

### Skill-Based Agent Design

Rather than monolithic prompting, we model the agent as a composition of reusable **skills**:

- Extracting tabular values
- Computing numeric differences
- Verifying calculations
- Cross-document aggregation

**EvoSkill Extension**: When failure patterns are detected, the LLM proposes new skills that address missing capabilities, validated and added to the skill library.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Bayesian Optimization Loop                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐ │
│  │ LLM Prior   │───▶│ Surrogate   │───▶│ Acquisition     │ │
│  │ (Configs)   │    │ Model       │    │ Function        │ │
│  └─────────────┘    └─────────────┘    └────────┬────────┘ │
└────────────────────────────────────────────────│───────────┘
                                                 │
                                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      Pipeline Evaluation                     │
│  ┌─────────┐   ┌──────────┐   ┌───────────┐   ┌──────────┐ │
│  │ Parsing │──▶│ Indexing │──▶│ Retrieval │──▶│ Reasoning│ │
│  └─────────┘   └──────────┘   └───────────┘   └──────────┘ │
└─────────────────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    Skill Library (EvoSkill)                  │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐ │
│  │ Table      │  │ Numeric    │  │ Cross-Document         │ │
│  │ Extraction │  │ Computation│  │ Aggregation            │ │
│  └────────────┘  └────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Two Complementary Improvement Loops

1. **Bayesian Optimization**: Efficiently searches over pipeline configurations and skill compositions
2. **EvoSkill Mechanism**: Expands the set of available skills based on failure analysis

The LLM serves as a source of prior knowledge for both:
- Suggests promising configurations for BO initialization
- Proposes candidate skills during failure analysis

## Evaluation

### Metrics
- Answer accuracy (fuzzy numeric matching with 1% tolerance)
- Number of evaluations required to reach target score
- Generalization of discovered skills across question types

### Baselines
- Manual pipeline design
- Random search over configurations
- Standard Bayesian optimization without LLM prior
- Fixed skill library vs. EvoSkill-augmented version

## Competition Details

- **Platform**: [Sentient Arena](https://arena.sentient.xyz)
- **Benchmark**: OfficeQA by Databricks
- **Dataset**: 246 questions across two difficulty levels
- **Scoring**: Fuzzy numeric matching with 1% tolerance
- **Duration**: March 14th - April 4th, 2026

## Quick Start

```bash
# Download CLI
curl -O https://arena.sentient.xyz/api/download/cli

# Authenticate
arena auth

# Initialize project
arena init
```

## Expected Contribution

This approach demonstrates how large language models can act as **knowledge priors for system design**, rather than merely inference engines. Beyond OfficeQA, the methodology offers a general strategy for building self-improving RAG agents capable of adapting both their infrastructure and capabilities as they encounter new problem domains.

## License

TBD

## References

- [Sentient Arena](https://arena.sentient.xyz)
- [OfficeQA Benchmark](https://www.databricks.com)
