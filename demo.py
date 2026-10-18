"""In-memory copy of the seeded graph, used only when FalkorDB is unreachable (e.g. the public Vercel demo).

Mirrors tools.subgraph() over the same synthetic data as seed.py. Chat/incident agents still need the real database.
"""
import random
from functools import cache

import seed


@cache
def _model():
    rnd = random.Random(7)  # same seed as seed.build -> identical tickets
    nodes, edges = {}, []
    by_team = {t: [p for p, _, pt in seed.PEOPLE if pt == t] for t in seed.TEAMS}

    def node(id_, label, name):
        nodes[id_] = {"id": id_, "label": label, "name": name}

    for t in seed.TEAMS:
        node(t, "Team", t)
    for sid, team, _, deps in seed.SERVICES:
        node(sid, "Service", sid)
        edges.append((team, sid, "OWNS"))
        edges += [(sid, d, "DEPENDS_ON") for d in deps]
    for i in range(1, 41):  # must consume rnd in the same order as seed.build
        svc, team, _, _ = rnd.choice(seed.SERVICES)
        pool = by_team[team] if rnd.random() < 0.75 else [p for p, _, _ in seed.PEOPLE]
        it = rnd.choice(seed.ISSUE_TYPES)
        rnd.choice(pool)  # the assignee; not drawn in the graph, but it advances the RNG like seed.build
        node(f"T-{i:03d}", "Ticket", f"{it.replace('_', ' ')} on {svc}")
        edges.append((f"T-{i:03d}", svc, "AFFECTS"))
    for sid, team, tier, _ in seed.SERVICES:
        if tier == 1:
            d = f"D-{[s[0] for s in seed.SERVICES].index(sid)}"
            node(d, "Document", f"Runbook: {sid}")
            edges.append((d, sid, "DOCUMENTS"))
    for did, title, sid in [
        ("DEC-1", "Move sessions from postgres to redis", "session-store"),
        ("DEC-2", "Shorten vault token TTL to 1h", "vault"),
        ("DEC-3", "Add retry with jitter to auth-service clients", "auth-service"),
        ("DEC-4", "Cap redis-cache maxmemory at 8GB", "redis-cache"),
        ("DEC-5", "Raise redis-cache maxmemory to 16GB", "redis-cache"),
        ("DEC-6", "Route checkout through fraud-detector synchronously", "checkout"),
    ]:
        node(did, "Decision", title)
        edges.append((did, sid, "CHANGED"))
    for cid, name, _, svcs in seed.CUSTOMERS:
        node(cid, "Customer", name)
        edges += [(cid, s, "USES") for s in svcs]
    return nodes, edges


def subgraph(service_id: str) -> dict:
    nodes, edges = _model()
    if service_id not in nodes:
        return {"nodes": [], "edges": []}
    keep = {service_id}
    frontier = {service_id}
    for _ in range(2):  # 2 undirected DEPENDS_ON hops between services
        frontier = {y for a, b, r in edges if r == "DEPENDS_ON" for x, y in ((a, b), (b, a)) if x in frontier} - keep
        keep |= frontier
    keep |= {x for a, b, r in edges if r in ("OWNS", "AFFECTS", "CHANGED") for x in (a, b) if service_id in (a, b)}
    return {"nodes": [nodes[i] for i in keep],
            "edges": [{"source": a, "target": b, "type": r} for a, b, r in edges if a in keep and b in keep]}
