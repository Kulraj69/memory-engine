"""Three-tier deterministic memory for long-running agents.

Tiers:
  working  - the live scratchpad: recent items verbatim, bounded size.
  episodic - compressed session history: extractive summaries with scores.
  semantic - keyword index over everything retained, for retrieval.

Eviction is scored, not random: expired (TTL) entries go first, then the
lowest score (recency + access frequency + pin bonus). Compression is
extractive - sentences are selected, never rewritten - so nothing is
hallucinated into memory. All deterministic: same operations, same state.
"""

import math
import re
import time
from dataclasses import dataclass, field

_WORD = re.compile(r"[a-z0-9]+")
_SENTENCE = re.compile(r"[^.!?]+[.!?]?")


def _tokens(text):
    return _WORD.findall(text.lower())


@dataclass
class Entry:
    content: str
    created: float
    kind: str = "episode"          # 'scratch' | 'episode'
    accesses: int = 0
    pinned: bool = False
    ttl: float = math.inf          # seconds; inf = never expires

    def score(self, now):
        if self.pinned:
            return math.inf
        age_hours = max(0.0, (now - self.created) / 3600.0)
        recency = 1.0 / (1.0 + age_hours)
        frequency = math.log1p(self.accesses)
        return recency + frequency

    def expired(self, now):
        return now - self.created > self.ttl

    def compressed(self, max_sentences=2, max_chars=200):
        sents = [s.strip() for s in _SENTENCE.findall(self.content) if s.strip()]
        picked = sents[:max_sentences]
        text = " ".join(picked)
        if len(text) > max_chars:
            text = text[: max_chars - 3].rstrip() + "..."
        return Entry(text, self.created, "episode", self.accesses, self.pinned, self.ttl)


class MemoryEngine:
    def __init__(self, working_capacity=10, episodic_capacity=100, default_ttl=math.inf, now=None):
        self.working_capacity = working_capacity
        self.episodic_capacity = episodic_capacity
        self.default_ttl = default_ttl
        self._now = now or time.time
        self._working = []   # list[Entry], newest last
        self._episodic = []  # list[Entry]

    # -- writes -------------------------------------------------------------

    def add(self, content, pinned=False, ttl=None):
        entry = Entry(content, self._now(), "scratch", 0, pinned,
                      self.default_ttl if ttl is None else ttl)
        self._working.append(entry)
        self._consolidate()
        return entry

    def _consolidate(self):
        """Overflow from working memory is compressed into episodic."""
        while len(self._working) > self.working_capacity:
            # Pinned entries stay; evict the oldest unpinned.
            victim = next((e for e in self._working if not e.pinned), None)
            if victim is None:
                break  # everything pinned: let it overflow rather than lose pins
            self._working.remove(victim)
            self._episodic.append(victim.compressed())
        self._evict_episodic()

    def _evict_episodic(self):
        now = self._now()
        self._episodic = [e for e in self._episodic if not e.expired(now)]
        while len(self._episodic) > self.episodic_capacity:
            victim = min(self._episodic, key=lambda e: e.score(now))
            if victim.pinned:
                break
            self._episodic.remove(victim)

    # -- reads --------------------------------------------------------------

    def retrieve(self, query, k=5):
        """Score every entry by keyword overlap + entry score; return top k."""
        q = set(_tokens(query))
        if not q:
            return []
        now = self._now()
        ranked = []
        for entry in list(self._working) + list(self._episodic):
            if entry.expired(now):
                continue
            toks = set(_tokens(entry.content))
            overlap = len(q & toks) / math.sqrt(max(1, len(toks)))
            if overlap == 0:
                continue
            entry.accesses += 1
            ranked.append((overlap + entry.score(now), entry))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in ranked[:k]]

    def working(self):
        return list(self._working)

    def episodic(self):
        return list(self._episodic)

    def tick(self):
        """Advance eviction without a write (drop expired entries)."""
        now = self._now()
        self._working = [e for e in self._working if not e.expired(now)]
        self._evict_episodic()
