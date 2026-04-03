---
name: sub-llm-verification
description: Sub-LLM verification tool for independent cross-checking of table extractions, value verification, and formula disambiguation. Uses a fresh LLM call via the OpenRouter API to get a second opinion on ambiguous data.
---
# Sub-LLM Verification Tool

This skill provides a **fresh, independent LLM** you can call from within the container to verify your extractions. The sub-LLM has zero memory of your prior reasoning — it sees only the context chunk you give it and answers from scratch. This eliminates confirmation bias.

## Setup: Creating /app/sub_llm.py

The file `/app/sub_llm.py` must exist before you can use it. Create it with this command:

```bash
cat > /app/sub_llm.py << 'PYEOF'
"""Sub-LLM helper for independent verification. Stdlib only — no pip needed."""
import json, urllib.request, os, sys

def sub_query(question, context, model="minimax/minimax-m2.5", max_tokens=400):
    url = "https://openrouter.ai/api/v1/chat/completions"
    key = os.environ.get("OPENROUTER_API_KEY", os.environ.get("LLM_API_KEY", ""))
    if not key:
        return "ERROR: No API key found"
    payload = json.dumps({
        "model": model, "temperature": 0.0, "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": "Answer precisely using ONLY the provided context. Be concise. Give just the answer value."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ]
    }).encode()
    req = urllib.request.Request(url, data=payload, method="POST", headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        "HTTP-Referer": "https://arena.sentient.xyz"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]
    except Exception as e:
        return f"ERROR: {e}"

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        q = sys.argv[1]
        with open(sys.argv[2]) as f: ctx = f.read()
        print(sub_query(q, ctx))
    elif len(sys.argv) == 2:
        import select
        ctx = sys.stdin.read() if select.select([sys.stdin], [], [], 0.0)[0] else ""
        print(sub_query(sys.argv[1], ctx))
PYEOF
```

## ⚠️ CRITICAL: Recovery from "No such file" Error

If you run `python3 /app/sub_llm.py ...` and get:
```
python3: can't open file '/app/sub_llm.py': [Errno 2] No such file or directory
```

**You MUST immediately create the file using the code block above, then retry your command.** Do NOT skip verification — create the file and try again.

## Usage

```bash
# 1. Save a chunk of context (20-40 lines around your extraction)
sed -n '380,410p' /app/corpus/treasury_bulletin_1992_06.txt > /tmp/chunk.txt

# 2. Ask the sub-LLM a specific question about that chunk
python3 /app/sub_llm.py "What table is this? What is the Total capital value?" /tmp/chunk.txt
```

## When to Use (max 2-3 calls per task)

### 1. Table Identity Verification
After extracting values from a table, confirm you have the RIGHT table. Multiple tables have similar row labels.

```bash
sed -n '380,410p' /app/corpus/treasury_bulletin_1992_06.txt > /tmp/chunk.txt
python3 /app/sub_llm.py "What table is this (e.g. ESF-1, FFO-1, FD-1)? What is the value in the 'Total capital' row?" /tmp/chunk.txt
```

Use this for: ESF questions, CAGR across tables, any question where you grep a row label that appears in multiple tables.

### 2. Value Extraction Cross-Check
When you extracted a number, have the sub-LLM independently extract it from the same chunk.

```bash
sed -n '395,425p' /app/corpus/treasury_bulletin_2013_12.txt > /tmp/chunk.txt
python3 /app/sub_llm.py "In this table, what is the value for 'Total assets' in the ending balance column? Report the raw number." /tmp/chunk.txt
```

Use this for: Multi-column tables where column alignment is ambiguous, values that seem duplicated, ESF balance sheets with 3 columns.

### 3. Formula Disambiguation
When the question uses ambiguous phrasing like "percent difference" vs "percent change".

```bash
echo "The question asks: 'What is the percent difference between A and B?' A=150, B=200." > /tmp/chunk.txt
python3 /app/sub_llm.py "Should I use symmetric percent difference |A-B|/((A+B)/2)*100 or simple percent change (B-A)/A*100? Which formula does 'percent difference' mean?" /tmp/chunk.txt
```

## Rules
- **NEVER use before writing a preliminary answer to /app/answer.txt.** Budget safety first.
- **Max 2-3 calls per task.** Each call takes ~3-5 seconds.
- **Keep chunks small.** 20-40 lines, not entire files.
- **If sub-LLM disagrees with you**, investigate — read the table header again. The sub-LLM has fresh eyes.
- **If sub-LLM returns ERROR**, ignore it and proceed with your own answer.
