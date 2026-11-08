"""Reproduces the demo video's real output: layered memory with TTL and pinning."""
from memory_engine import MemoryEngine

clock = [1000.0]
me = MemoryEngine(working_capacity=5, episodic_capacity=50, now=lambda: clock[0])
ADDS = [("Kulraj prefers window seats on flights", {"pinned": True}),
        ("Booked BLR-DEL IndiGo 06:10 on Nov 8", {}),
        ("Likes minimal Apple-style design", {}),
        ("Working on 14 agent-infra repos", {}),
        ("temp note: standup at 5pm today", {"ttl": 3600}),
        ("Favorite airline: IndiGo", {})]
if __name__ == "__main__":
    for content, kw in ADDS:
        me.add(content, **kw)
        print("add:", content)
    print('retrieve("window seats flights") ->')
    for e in me.retrieve("window seats flights", k=3):
        print("  ", e.content, "[pinned]" if e.pinned else "")
    print('retrieve("IndiGo") ->')
    for e in me.retrieve("IndiGo", k=3):
        print("  ", e.content)
    clock[0] += 3700
    me.tick()
    r = me.retrieve("standup", k=3)
    print('retrieve("standup") ->', r[0].content if r else "(expired - no results)")
