# memory-engine

Three-tier deterministic memory for long-running agents. Offline, standard
library only, no model calls.

Covers the "3-Tier Memory & Eviction Engine" item: working scratchpad,
episodic session compression and scored retrieval with TTL eviction.
Infinite context causes OOM and hallucination; memory has to be managed.

```python
from memory_engine import MemoryEngine

mem = MemoryEngine(working_capacity=10, episodic_capacity=100, default_ttl=3600)
mem.add("user prefers concise answers", pinned=True)
mem.add("deploy failed on friday at 5pm")
hits = mem.retrieve("deploy failure")   # scored: keyword overlap + recency + frequency
```

Tiers and rules:
- **Working**: recent items verbatim, bounded; overflow is compressed into
  episodic. Pinned entries are never evicted.
- **Episodic**: extractive compression (sentences selected, never rewritten -
  nothing hallucinated into memory), capacity-bounded by score.
- **Retrieval**: keyword overlap normalized by length, plus recency and
  access frequency. Fully deterministic: same operations, same results.

Honest scope: scoring is heuristic (recency + frequency + overlap), not
learned relevance. Swapping the scorer for embeddings is a drop-in upgrade;
the eviction and consolidation logic stays.

## Tests

```
python3 -m unittest discover -s tests
```

## Demo

`demo.py` reproduces the recorded demo run end to end, offline (standard
library only, no model calls):

    python demo.py

It executes the library's real code path and prints the same output shown in
the recorded demo video.
