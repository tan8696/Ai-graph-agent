"""Seed one tenant graph with a small, hand-written DevOps company.

Run: python seed.py [tenant]   (default tenant: acme)
Wipes and rebuilds graph `tenant_<tenant>`.
"""
import random
import sys

from tools import graph

TEAMS = ["platform", "payments", "identity", "data", "edge"]

PEOPLE = [  # (id, name, team)
    ("p1", "Asha Rao", "platform"), ("p2", "Ben Ortiz", "platform"), ("p3", "Chen Wei", "platform"),
    ("p4", "Dana Kim", "payments"), ("p5", "Eli Novak", "payments"), ("p6", "Fatima Ali", "payments"),
    ("p7", "Gus Moreno", "identity"), ("p8", "Hana Sato", "identity"), ("p9", "Ivan Petrov", "identity"),
    ("p10", "Jo Smith", "data"), ("p11", "Kiran Das", "data"), ("p12", "Lena Fischer", "data"),
    ("p13", "Mo Haddad", "edge"), ("p14", "Nia Brooks", "edge"), ("p15", "Omar Siddiqui", "edge"),
]

SERVICES = [  # (id, owning team, tier, depends_on)
    ("postgres-main", "platform", 1, []),
    ("redis-cache", "platform", 1, []),
    ("kafka", "platform", 1, []),
    ("k8s-cluster", "platform", 1, []),
    ("vault", "platform", 1, ["k8s-cluster"]),
    ("service-mesh", "platform", 1, ["k8s-cluster"]),
    ("object-store", "platform", 2, []),
    ("auth-service", "identity", 1, ["postgres-main", "redis-cache", "vault"]),
    ("user-profile", "identity", 2, ["postgres-main", "auth-service"]),
    ("session-store", "identity", 1, ["redis-cache"]),
    ("sso-gateway", "identity", 1, ["auth-service", "session-store"]),
    ("mfa-service", "identity", 2, ["auth-service"]),
    ("payment-gateway", "payments", 1, ["auth-service", "postgres-main", "kafka", "vault"]),
    ("ledger", "payments", 1, ["postgres-main", "kafka"]),
    ("billing", "payments", 2, ["ledger", "user-profile"]),
    ("fraud-detector", "payments", 1, ["kafka", "feature-store"]),
    ("invoice-renderer", "payments", 3, ["billing", "object-store"]),
    ("refunds", "payments", 2, ["payment-gateway", "ledger"]),
    ("event-pipeline", "data", 1, ["kafka", "object-store"]),
    ("feature-store", "data", 2, ["redis-cache", "event-pipeline"]),
    ("analytics-warehouse", "data", 2, ["event-pipeline"]),
    ("reporting-api", "data", 3, ["analytics-warehouse", "auth-service"]),
    ("search-index", "data", 2, ["event-pipeline", "user-profile"]),
    ("api-gateway", "edge", 1, ["auth-service", "service-mesh", "rate-limiter"]),
    ("rate-limiter", "edge", 1, ["redis-cache"]),
    ("cdn-edge", "edge", 1, ["object-store"]),
    ("web-frontend", "edge", 1, ["api-gateway", "cdn-edge", "sso-gateway"]),
    ("mobile-bff", "edge", 1, ["api-gateway", "payment-gateway", "user-profile"]),
    ("checkout", "edge", 1, ["payment-gateway", "fraud-detector", "api-gateway"]),
    ("notifications", "edge", 2, ["kafka", "user-profile"]),
]

ISSUE_TYPES = ["latency", "outage", "memory_leak", "auth_failure", "data_loss", "config_drift"]

PLAYBOOKS = {  # issue_type -> ordered steps (procedural memory)
    "latency": ["Check p99 on the service dashboard", "Check replica health on postgres-main",
                "Scale out the slowest dependency", "Roll back the last deploy if p99 does not recover"],
    "outage": ["Page the owning team on-call", "Fail over to the standby region",
               "Freeze deploys for downstream services", "Open a status-page incident"],
    "memory_leak": ["Capture a heap dump from one pod", "Restart pods in a rolling fashion",
                    "Pin the previous image tag", "File a ticket with the heap dump attached"],
    "auth_failure": ["Check vault token expiry", "Check auth-service error rate by client",
                     "Rotate the signing key if tokens fail validation", "Purge session-store if sessions are stale"],
    "data_loss": ["Stop writers to the affected store", "Snapshot the current state",
                  "Restore from the last good backup to a side instance", "Reconcile with the ledger"],
    "config_drift": ["Diff live config against git", "Re-apply the declared config",
                     "Add a drift alert for the key that changed"],
}
FALLBACKS = {  # (issue_type, step number) -> what to do if that step fails: the branch agents may rewire
    ("latency", 2): "Page platform on-call (DevOps)",
    ("auth_failure", 1): "Page identity on-call",
    ("outage", 2): "Page platform on-call (DevOps)",
}

CUSTOMERS = [  # (id, name, vip, services they call)
    ("C-globex", "Globex Corp", True, ["checkout", "mobile-bff"]),
    ("C-initech", "Initech", True, ["reporting-api", "web-frontend"]),
    ("C-umbrella", "Umbrella Health", True, ["sso-gateway"]),
    ("C-hooli", "Hooli", False, ["web-frontend"]),
    ("C-piedpiper", "Pied Piper", False, ["notifications", "search-index"]),
]


def build(tenant: str) -> None:
    rnd = random.Random(7)  # fixed seed so demos are repeatable
    g = graph(tenant)
    try:
        g.delete()
    except Exception:
        pass  # graph did not exist yet
    g = graph(tenant)

    g.query("UNWIND $t AS t CREATE (:Team {id: t, name: t})", {"t": TEAMS})
    g.query("""UNWIND $p AS p MATCH (t:Team {id: p[2]})
               CREATE (:Person {id: p[0], name: p[1], team: p[2]})-[:MEMBER_OF]->(t)""", {"p": PEOPLE})
    g.query("""UNWIND $s AS s MATCH (t:Team {id: s[1]})
               CREATE (t)-[:OWNS]->(:Service {id: s[0], name: s[0], tier: s[2]})""",
            {"s": [[s, t, tier] for s, t, tier, _ in SERVICES]})
    g.query("""UNWIND $e AS e MATCH (a:Service {id: e[0]}), (b:Service {id: e[1]})
               CREATE (a)-[:DEPENDS_ON]->(b)""",
            {"e": [[s, d] for s, _, _, deps in SERVICES for d in deps]})

    # Tickets: mostly resolved by the owning team, sometimes by someone cross-team.
    tickets = []
    by_team = {t: [p for p, _, pt in PEOPLE if pt == t] for t in TEAMS}
    for i in range(1, 41):
        svc, team, _, _ = rnd.choice(SERVICES)
        owner_pool = by_team[team] if rnd.random() < 0.75 else [p for p, _, _ in PEOPLE]
        it = rnd.choice(ISSUE_TYPES)
        tickets.append([f"T-{i:03d}", f"{it.replace('_', ' ')} on {svc}", it, svc, rnd.choice(owner_pool)])
    g.query("""UNWIND $t AS t MATCH (s:Service {id: t[3]}), (p:Person {id: t[4]})
               CREATE (p)-[:RESOLVED]->(:Ticket {id: t[0], title: t[1], issue_type: t[2], status: 'closed'})-[:AFFECTS]->(s)""",
            {"t": tickets})

    # Company brain: docs and decision lineage.
    docs = [[f"D-{i}", f"Runbook: {s}", s, rnd.choice(by_team[t])] for i, (s, t, tier, _) in enumerate(SERVICES) if tier == 1]
    g.query("""UNWIND $d AS d MATCH (s:Service {id: d[2]}), (p:Person {id: d[3]})
               CREATE (p)-[:AUTHORED]->(:Document {id: d[0], title: d[1]})-[:DOCUMENTS]->(s)""", {"d": docs})
    decisions = [
        ["DEC-1", "Move sessions from postgres to redis", "2025-03-02", "session-store", "p8", None],
        ["DEC-2", "Shorten vault token TTL to 1h", "2025-09-14", "vault", "p1", None],
        ["DEC-3", "Add retry with jitter to auth-service clients", "2026-01-20", "auth-service", "p7", None],
        ["DEC-4", "Cap redis-cache maxmemory at 8GB", "2026-04-11", "redis-cache", "p2", None],
        ["DEC-5", "Raise redis-cache maxmemory to 16GB", "2026-07-30", "redis-cache", "p3", "DEC-4"],
        ["DEC-6", "Route checkout through fraud-detector synchronously", "2026-08-05", "checkout", "p4", None],
    ]
    g.query("""UNWIND $d AS d MATCH (s:Service {id: d[3]}), (p:Person {id: d[4]})
               CREATE (p)-[:MADE]->(:Decision {id: d[0], title: d[1], date: d[2]})-[:CHANGED]->(s)""", {"d": decisions})
    g.query("""UNWIND $d AS d MATCH (a:Decision {id: d[0]}), (b:Decision {id: d[1]})
               CREATE (a)-[:SUPERSEDES]->(b)""", {"d": [[d[0], d[5]] for d in decisions if d[5]]})

    g.query("""UNWIND $c AS c CREATE (cu:Customer {id: c[0], name: c[1], vip: c[2]})
               WITH cu, c UNWIND c[3] AS sid MATCH (s:Service {id: sid}) CREATE (cu)-[:USES]->(s)""",
            {"c": [list(c) for c in CUSTOMERS]})

    # Procedural memory as an executable chain: (:Playbook)-[:FIRST]->(step)-[:NEXT]->(step), with -[:IF_FAILS]-> branches.
    g.query("UNWIND $pb AS it CREATE (:Playbook {id: 'PB-' + it, issue_type: it})", {"pb": list(PLAYBOOKS)})
    steps = [[f"R-{it}-{i}", text, it, i] for it, v in PLAYBOOKS.items() for i, text in enumerate(v, 1)]
    g.query("UNWIND $s AS s CREATE (:ActionRule {id: s[0], text: s[1]})", {"s": steps})
    g.query("""UNWIND $s AS s MATCH (p:Playbook {issue_type: s[2]}), (r:ActionRule {id: s[0]})
               WITH p, r, s WHERE s[3] = 1 CREATE (p)-[:FIRST]->(r)""", {"s": steps})
    g.query("""UNWIND $s AS s MATCH (a:ActionRule {id: s[0]}), (b:ActionRule {id: s[1]}) CREATE (a)-[:NEXT]->(b)""",
            {"s": [[f"R-{it}-{i}", f"R-{it}-{i + 1}"] for it, v in PLAYBOOKS.items() for i in range(1, len(v))]})
    g.query("""UNWIND $f AS f MATCH (a:ActionRule {id: f[0]})
               CREATE (a)-[:IF_FAILS]->(:ActionRule {id: f[0] + '-f', text: f[1]})""",
            {"f": [[f"R-{it}-{n}", text] for (it, n), text in FALLBACKS.items()]})

    # Episodic memory: one past incident session so recall_memory has something to find.
    g.query("""MATCH (s:Service {id: 'auth-service'})
               CREATE (:Session {id: 'S-seed', started: '2026-06-02T10:00:00Z'})-[:LOGGED_EVENT]->
                      (e:Episode {id: 'E-seed', ts: '2026-06-02T10:40:00Z', agent: 'remediation', issue_type: 'auth_failure',
                       summary: 'Vault token TTL expiry broke auth-service; rotated token, Gus Moreno resolved in 25m'})-[:ABOUT]->(s)""")


if __name__ == "__main__":
    tenant = sys.argv[1] if len(sys.argv) > 1 else "acme"
    build(tenant)
    counts = graph(tenant).query("MATCH (n) RETURN labels(n)[0] AS l, count(n) ORDER BY l").result_set
    print(f"seeded tenant_{tenant}:", dict(counts))
