import math
import unittest

from memory_engine import MemoryEngine


def engine(cap=3, ecap=5, ttl=math.inf, start=1000.0):
    state = {"t": start}
    e = MemoryEngine(working_capacity=cap, episodic_capacity=ecap,
                     default_ttl=ttl, now=lambda: state["t"])
    return e, state


class TestWorkingMemory(unittest.TestCase):
    def test_bounded(self):
        e, _ = engine(cap=3)
        for i in range(5):
            e.add("note %d" % i)
        self.assertEqual(len(e.working()), 3)

    def test_overflow_compresses_to_episodic(self):
        e, _ = engine(cap=2)
        e.add("first note. with extra sentence here.")
        e.add("second note.")
        e.add("third note.")
        self.assertEqual(len(e.episodic()), 1)
        self.assertEqual(e.episodic()[0].kind, "episode")

    def test_compression_truncates(self):
        e, _ = engine(cap=1)
        long = " ".join("sentence %d is here." % i for i in range(20))
        e.add(long)
        e.add("bump")
        self.assertLessEqual(len(e.episodic()[0].content), 200)

    def test_pinned_never_evicted_from_working(self):
        e, _ = engine(cap=2)
        e.add("keep me", pinned=True)
        for i in range(5):
            e.add("filler %d" % i)
        self.assertTrue(any(x.pinned for x in e.working()))


class TestEviction(unittest.TestCase):
    def test_ttl_expires(self):
        e, st = engine(cap=10, ttl=100.0)
        e.add("short lived fact")
        st["t"] += 200.0
        e.tick()
        self.assertEqual(e.working(), [])

    def test_episodic_capacity_scored_eviction(self):
        e, _ = engine(cap=1, ecap=2)
        for i in range(10):
            e.add("memory item %d" % i)
        self.assertLessEqual(len(e.episodic()), 2)

    def test_frequently_accessed_survives(self):
        e, st = engine(cap=2, ecap=2)
        e.add("important reference material")
        e.retrieve("reference")          # boost its access count
        e.add("filler one")
        e.add("filler two")
        e.add("filler three")
        st["t"] += 10.0
        for i in range(5):
            e.add("more filler %d" % i)
        contents = [x.content for x in e.episodic()]
        self.assertTrue(any("important" in c for c in contents))


class TestRetrieval(unittest.TestCase):
    def test_keyword_match(self):
        e, _ = engine()
        e.add("the deploy failed on friday")
        e.add("lunch was pizza")
        hits = e.retrieve("deploy failure")
        self.assertEqual(hits[0].content, "the deploy failed on friday")

    def test_no_match_returns_empty(self):
        e, _ = engine()
        e.add("nothing relevant here")
        self.assertEqual(e.retrieve("zzz qqq"), [])

    def test_recency_breaks_ties(self):
        e, st = engine(cap=10)
        e.add("budget report alpha")
        st["t"] += 100.0
        e.add("budget report beta")
        hits = e.retrieve("budget report")
        self.assertEqual(hits[0].content, "budget report beta")

    def test_deterministic(self):
        e1, _ = engine()
        e2, _ = engine()
        for m in (e1, e2):
            m.add("alpha beta gamma")
            m.add("delta epsilon")
        self.assertEqual([x.content for x in e1.retrieve("alpha")],
                         [x.content for x in e2.retrieve("alpha")])


if __name__ == "__main__":
    unittest.main()
