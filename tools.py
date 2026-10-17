"""Graph tools shared by the MCP server, the agents and the web app.

Every function takes a tenant and returns plain JSON-able data.
"""
import os
import re
import uuid
from datetime import datetime, timezone
from functools import cache

from falkordb import FalkorDB

# shortcut: minimal KEY=VALUE .env reader (no quotes or export); real env vars win. Use python-dotenv if .env grows.
_ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_ENV):
    for _line in open(_ENV, encoding="utf-8"):
        _k, _sep, _v = _line.strip().partition("=")
        if _sep and not _k.startswith("#"):
            os.environ.setdefault(_k.strip(), _v.strip())


@cache
def _db() -> FalkorDB:
    return FalkorDB.from_url(os.environ.get("FALKORDB_URL", "redis://localhost:6379"))


def graph(tenant: str):
    # One graph per tenant: data isolation without separate databases.
    return _db().select_graph(f"tenant_{tenant}")


def _rows(tenant: str, q: str, params: dict | None = None) -> list[list]:
    return graph(tenant).query(q, params or {}).result_set


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def criticality(tenant: str) -> dict[str, float]:
    """PageRank over DEPENDS_ON: services many things lean on score high."""
    rows = _rows(tenant, "CALL algo.pageRank('Service', 'DEPENDS_ON') YIELD node, score RETURN node.id, score")
    return {sid: round(score, 4) for sid, score in rows}


def get_blast_radius(tenant: str, service_id: str, max_hops: int = 3) -> dict:
    max_hops = max(1, min(int(max_hops), 6))  # hop count is interpolated, so clamp it
    rows = _rows(tenant, f"""
        MATCH p = (up:Service)-[:DEPENDS_ON*1..{max_hops}]->(s:Service {{id: $id}})
        WITH up, min(length(p)) AS hops
        OPTIONAL MATCH (t:Team)-[:OWNS]->(up)
        RETURN up.id, up.tier, hops, t.id ORDER BY hops, up.tier""", {"id": service_id})
    rank = criticality(tenant)
    impacted = [{"service": s, "tier": tier, "hops": h, "owner_team": team, "pagerank": rank.get(s, 0)}
                for s, tier, h, team in rows]
    return {"service": service_id, "impacted_count": len(impacted),
            "tier1_impacted": [i["service"] for i in impacted if i["tier"] == 1],
            "impacted": impacted, "customers": _customer_paths(tenant, [service_id])}


def _customer_paths(tenant: str, service_ids: list[str]) -> list[dict]:
    """Customers whose services reach any of service_ids over DEPENDS_ON, with the shortest path as proof."""
    rows = _rows(tenant, """
        MATCH (d:Service) WHERE d.id IN $ids
        MATCH p = (c:Customer)-[:USES]->(:Service)-[:DEPENDS_ON*0..4]->(d)
        RETURN c.id, c.name, c.vip, [n IN nodes(p) | n.id], length(p) AS hops ORDER BY hops""", {"ids": service_ids})
    seen = {}
    for cid, name, vip, path, _ in rows:
        seen.setdefault(cid, {"customer": cid, "name": name, "vip": bool(vip), "path": path})
    return list(seen.values())


def find_expert_path(tenant: str, service_id: str, issue_type: str) -> dict:
    """People who fixed this kind of issue on this service or a direct neighbour, with the path as evidence."""
    rows = _rows(tenant, """
        MATCH (target:Service {id: $id})
        MATCH (p:Person)-[:RESOLVED]->(t:Ticket {issue_type: $it})-[:AFFECTS]->(s:Service)
        WHERE s = target OR (s)-[:DEPENDS_ON]-(target)
        RETURN p.id, p.name, p.team, count(DISTINCT t) AS n,
               collect(DISTINCT p.name + ' -RESOLVED-> ' + t.id + ' -AFFECTS-> ' + s.id) AS paths
        ORDER BY n DESC LIMIT 5""", {"id": service_id, "it": issue_type})
    experts = [{"person_id": pid, "name": name, "team": team, "tickets": n, "evidence": paths[:3]}
               for pid, name, team, n, paths in rows]
    owners = _rows(tenant, """MATCH (t:Team)-[:OWNS]->(:Service {id: $id})
                              MATCH (p:Person)-[:MEMBER_OF]->(t) RETURN t.id, collect(p.name)""", {"id": service_id})
    return {"service": service_id, "issue_type": issue_type, "experts": experts,
            "owning_team": {"team": owners[0][0], "members": owners[0][1]} if owners else None}


def decision_lineage(tenant: str, service_id: str) -> list[dict]:
    """Who decided what about this service, newest first, with what it superseded."""
    rows = _rows(tenant, """
        MATCH (p:Person)-[:MADE]->(d:Decision)-[:CHANGED]->(:Service {id: $id})
        OPTIONAL MATCH (d)-[:SUPERSEDES]->(old:Decision)
        RETURN d.id, d.title, d.date, p.name, old.title ORDER BY d.date DESC""", {"id": service_id})
    return [{"id": i, "title": t, "date": dt, "by": by, "supersedes": old} for i, t, dt, by, old in rows]


def recall_memory(tenant: str, service_id: str, issue_type: str) -> dict:
    """Episodic (past incidents on this service) + procedural (playbook steps) memory."""
    episodes = _rows(tenant, """
        MATCH (e:Episode)-[:ABOUT]->(:Service {id: $id})
        RETURN e.ts, e.agent, e.issue_type, e.summary ORDER BY e.ts DESC LIMIT 5""", {"id": service_id})
    return {"episodes": [{"ts": ts, "agent": a, "issue_type": it, "summary": s} for ts, a, it, s in episodes],
            "playbook": get_runbook(tenant, issue_type)["steps"]}


def _step(i, text, by, why) -> dict:
    return {"id": i, "do": text, **({"changed_by": by, "reason": why} if by or why else {})}


def get_runbook(tenant: str, issue_type: str) -> dict:
    """Procedural memory as a graph: (:Playbook)-[:FIRST]->(step)-[:NEXT]->(step)..., each step may have -[:IF_FAILS]->."""
    rows = _rows(tenant, """
        MATCH (:Playbook {issue_type: $it})-[:FIRST]->(f:ActionRule)
        MATCH p = (f)-[:NEXT*0..20]->(r:ActionRule)
        OPTIONAL MATCH (r)-[:IF_FAILS]->(alt:ActionRule)
        RETURN r.id, r.text, r.changed_by, r.reason, alt.id, alt.text, alt.changed_by, alt.reason, length(p) AS pos
        ORDER BY pos""", {"it": issue_type})
    return {"issue_type": issue_type,
            "steps": [{**_step(i, t, by, why), "if_fails": _step(ai, at, aby, awhy) if ai else None}
                      for i, t, by, why, ai, at, aby, awhy, _ in rows]}


def update_runbook(tenant: str, issue_type: str, op: str, step_id: str, text: str = "",
                   reason: str = "", changed_by: str = "") -> dict:
    """Rewire the runbook graph. op: replace | insert_after | remove | set_fallback (empty text clears the fallback)."""
    # shortcut: several queries, not one transaction; fine for one operator at a time, fold into one Cypher per op under concurrency.
    found = _rows(tenant, """MATCH (:Playbook {issue_type: $it})-[:FIRST]->(:ActionRule)-[:NEXT*0..20]->(s:ActionRule {id: $sid})
                             RETURN count(s)""", {"it": issue_type, "sid": step_id})
    if not found or not found[0][0]:
        raise ValueError(f"no step {step_id} in the {issue_type} runbook; call get_runbook for step ids")
    if op in ("replace", "insert_after") and not text.strip():
        raise ValueError(f"{op} needs text")
    p = {"sid": step_id, "nid": f"R-{uuid.uuid4().hex[:6]}", "text": text, "by": changed_by, "why": reason, "now": _now()}
    props = "{id: $nid, text: $text, changed_by: $by, reason: $why, updated: $now}"
    if op == "replace":
        _rows(tenant, "MATCH (s:ActionRule {id: $sid}) SET s.text = $text, s.changed_by = $by, s.reason = $why, s.updated = $now", p)
    elif op == "set_fallback":
        _rows(tenant, "MATCH (:ActionRule {id: $sid})-[:IF_FAILS]->(old) DETACH DELETE old", p)
        if text.strip():
            _rows(tenant, f"MATCH (s:ActionRule {{id: $sid}}) CREATE (s)-[:IF_FAILS]->(:ActionRule {props})", p)
    elif op == "insert_after":
        nxt = _rows(tenant, "MATCH (:ActionRule {id: $sid})-[:NEXT]->(n) RETURN n.id", p)
        _rows(tenant, f"MATCH (s:ActionRule {{id: $sid}}) CREATE (s)-[:NEXT]->(:ActionRule {props})", p)
        if nxt:
            _rows(tenant, """MATCH (:ActionRule {id: $sid})-[r:NEXT]->(old:ActionRule {id: $old}), (n:ActionRule {id: $nid})
                             DELETE r CREATE (n)-[:NEXT]->(old)""", {**p, "old": nxt[0][0]})
    elif op == "remove":
        rel, nxt = _rows(tenant, """MATCH ()-[r:NEXT|FIRST]->(s:ActionRule {id: $sid}) OPTIONAL MATCH (s)-[:NEXT]->(n)
                                    RETURN type(r), n.id""", p)[0]
        if rel == "FIRST" and nxt is None:
            raise ValueError("cannot remove the only step of a runbook")
        if nxt:  # rel comes from the DB and is FIRST or NEXT, so interpolating it is safe
            _rows(tenant, f"""MATCH (prev)-[:{rel}]->(:ActionRule {{id: $sid}})-[:NEXT]->(n:ActionRule {{id: $n}})
                              CREATE (prev)-[:{rel}]->(n)""", {**p, "n": nxt})
        _rows(tenant, "MATCH (s:ActionRule {id: $sid}) OPTIONAL MATCH (s)-[:IF_FAILS]->(f) DETACH DELETE s, f", p)
    else:
        raise ValueError(f"unknown op {op}; use replace, insert_after, remove or set_fallback")
    return get_runbook(tenant, issue_type)


def compare_actions(tenant: str, action_a: str, takes_down_a: list[str], action_b: str, takes_down_b: list[str],
                    incident_id: str = "") -> dict:
    """Counterfactual sandbox: for each candidate action, which services go dark, which customers (VIPs first) feel it,
    and the PageRank risk. Picks the safer one; with an incident id, stores a DecisionReceipt on it."""
    takes_down_a = [s.strip() for s in (takes_down_a or []) if isinstance(s, str) and s.strip()]
    takes_down_b = [s.strip() for s in (takes_down_b or []) if isinstance(s, str) and s.strip()]
    ids = set(takes_down_a) | set(takes_down_b)
    known = {r[0] for r in _rows(tenant, "MATCH (s:Service) WHERE s.id IN $ids RETURN s.id", {"ids": list(ids)})}
    if ids - known:
        raise ValueError(f"unknown services: {sorted(ids - known)}")
    rank = criticality(tenant)

    def impact(name, down):
        svcs = set(down) | {i["service"] for d in down for i in get_blast_radius(tenant, d, 4)["impacted"]}
        cust = _customer_paths(tenant, list(down)) if down else []
        return {"action": name, "takes_down": down, "services_down": sorted(svcs),
                "customers_hit": [c["name"] for c in cust], "vip_hit": [c["name"] for c in cust if c["vip"]],
                "risk": round(sum(rank.get(x, 0) for x in svcs), 3), "paths": [c["path"] for c in cust]}

    a, b = impact(action_a, takes_down_a), impact(action_b, takes_down_b)
    score = lambda o: (len(o["vip_hit"]), len(o["customers_hit"]), o["risk"])
    chosen, rejected = (a, b) if score(a) <= score(b) else (b, a)
    why = (f"'{chosen['action']}' hits {len(chosen['vip_hit'])} VIP / {len(chosen['customers_hit'])} customers "
           f"(risk {chosen['risk']}); '{rejected['action']}' would hit {len(rejected['vip_hit'])} VIP "
           f"({', '.join(rejected['vip_hit']) or 'none'}) / {len(rejected['customers_hit'])} customers (risk {rejected['risk']})")
    out = {"chosen": chosen, "rejected": rejected, "why": why}
    if incident_id:
        rid = f"DR-{uuid.uuid4().hex[:6]}"
        if not _rows(tenant, """MATCH (i:Incident {id: $iid})
                                CREATE (:DecisionReceipt {id: $rid, chosen: $c, rejected: $r, why: $why, ts: $now})-[:FOR]->(i)
                                RETURN i.id""",
                     {"iid": incident_id, "rid": rid, "c": chosen["action"], "r": rejected["action"], "why": why, "now": _now()}):
            raise ValueError(f"no incident {incident_id}")
        out["receipt_id"] = rid
    return out


def create_incident(tenant: str, service_id: str, issue_type: str, summary: str,
                    suspected_root_cause: str = "", candidate_assignees: list[str] | None = None) -> dict:
    """Shared handoff state: the triage agent writes it, the remediation agent picks it up."""
    iid = f"INC-{uuid.uuid4().hex[:6]}"
    rows = _rows(tenant, """
        MATCH (s:Service {id: $sid})
        CREATE (i:Incident {id: $iid, issue_type: $it, summary: $summary, root_cause: $rc,
                            candidates: $cands, status: 'triaged', created: $now})-[:AFFECTS]->(s)
        RETURN i.id""",
          {"sid": service_id, "iid": iid, "it": issue_type, "summary": summary, "rc": suspected_root_cause,
           "cands": candidate_assignees or [], "now": _now()})
    if not rows:  # raising makes MCP return is_error=True, so the agent sees the failure
        raise ValueError(f"no service {service_id}")
    return {"incident_id": iid, "status": "triaged"}


def get_incident(tenant: str, incident_id: str) -> dict:
    rows = _rows(tenant, """
        MATCH (i:Incident {id: $id})-[:AFFECTS]->(s:Service)
        OPTIONAL MATCH (p:Person)-[:ASSIGNED_TO]->(i)
        RETURN i.id, s.id, i.issue_type, i.summary, i.root_cause, i.candidates, i.status, i.plan, p.name""",
                 {"id": incident_id})
    if not rows:
        raise ValueError(f"no incident {incident_id}")
    keys = ["incident_id", "service", "issue_type", "summary", "suspected_root_cause",
            "candidate_assignees", "status", "plan", "assignee"]
    return dict(zip(keys, rows[0]))


def assign_incident(tenant: str, incident_id: str, person_id: str, plan: list[str]) -> dict:
    rows = _rows(tenant, """
        MATCH (i:Incident {id: $iid}), (p:Person {id: $pid})
        OPTIONAL MATCH (:Person)-[old:ASSIGNED_TO]->(i)
        DELETE old
        WITH DISTINCT i, p
        SET i.status = 'assigned', i.plan = $plan
        CREATE (p)-[:ASSIGNED_TO {at: $now}]->(i)
        RETURN p.name""", {"iid": incident_id, "pid": person_id, "plan": plan, "now": _now()})
    if not rows:
        raise ValueError(f"incident {incident_id} or person {person_id} not found")
    return {"assigned_to": rows[0][0], "status": "assigned"}


def log_episode(tenant: str, session_id: str, agent: str, service_id: str, issue_type: str, summary: str) -> dict:
    """Write episodic memory so the next incident on this service can recall it."""
    eid = f"E-{uuid.uuid4().hex[:6]}"
    rows = _rows(tenant, """
        MATCH (s:Service {id: $svc})
        MERGE (sess:Session {id: $sid}) ON CREATE SET sess.started = $now
        CREATE (sess)-[:LOGGED_EVENT]->(e:Episode {id: $eid, ts: $now, agent: $agent, issue_type: $it,
                                                   summary: $summary})-[:ABOUT]->(s)
        RETURN e.id""",
          {"sid": session_id, "now": _now(), "svc": service_id, "eid": eid, "agent": agent,
           "it": issue_type, "summary": summary})
    if not rows:  # service check first, so a bad id leaves no orphan Session behind
        raise ValueError(f"no service {service_id}")
    return {"episode_id": eid}


def search_knowledge(tenant: str, query: str) -> list[dict]:
    """Keyword search over services, people, teams, tickets, docs, decisions, incidents and episodes,
    each with its direct graph links so the agent knows where to hop next."""
    # shortcut: substring match, no ranking beyond word hits. Swap for FalkorDB full-text or vector index at scale.
    words = [w for w in re.findall(r"[a-z0-9-]+", query.lower()) if len(w) > 2][:8]
    if not words:
        return []
    rows = _rows(tenant, """
        MATCH (n) WHERE n:Service OR n:Person OR n:Team OR n:Ticket OR n:Document OR n:Decision OR n:Incident OR n:Episode OR n:Customer
        WITH n, toLower(n.id + ' ' + coalesce(n.title, n.summary, n.name, '')) AS txt
        WITH n, size([w IN $words WHERE txt CONTAINS w]) AS hits WHERE hits > 0
        OPTIONAL MATCH (n)-[r]-(m)
        RETURN labels(n)[0], n.id, coalesce(n.title, n.summary, n.name, n.id), hits,
               collect(DISTINCT CASE WHEN startNode(r) = n THEN '-' + type(r) + '-> ' + m.id
                                     ELSE '<-' + type(r) + '- ' + m.id END)[0..8]
        ORDER BY hits DESC LIMIT 12""", {"words": words})
    return [{"type": t, "id": i, "text": txt, "links": links} for t, i, txt, _, links in rows]


def service_overview(tenant: str, service_id: str) -> dict:
    """Who owns a service, who is on that team, what it depends on, what depends on it, its runbooks and incidents."""
    rows = _rows(tenant, """
        MATCH (s:Service {id: $id})
        OPTIONAL MATCH (t:Team)-[:OWNS]->(s)
        OPTIONAL MATCH (t)<-[:MEMBER_OF]-(p:Person)
        OPTIONAL MATCH (s)-[:DEPENDS_ON]->(d:Service)
        OPTIONAL MATCH (u:Service)-[:DEPENDS_ON]->(s)
        RETURN s.tier, t.id, collect(DISTINCT p.id + ' ' + p.name), collect(DISTINCT d.id), collect(DISTINCT u.id)""",
                 {"id": service_id})
    if not rows:
        raise ValueError(f"no service {service_id}")
    tier, team, members, deps, dependents = rows[0]
    docs = _rows(tenant, """MATCH (p:Person)-[:AUTHORED]->(d:Document)-[:DOCUMENTS]->(:Service {id: $id})
                            RETURN d.id, d.title, p.name""", {"id": service_id})
    incidents = _rows(tenant, """MATCH (i:Incident)-[:AFFECTS]->(:Service {id: $id})
                                 OPTIONAL MATCH (p:Person)-[:ASSIGNED_TO]->(i)
                                 RETURN i.id, i.status, i.summary, p.name ORDER BY i.created DESC LIMIT 5""",
                      {"id": service_id})
    return {"service": service_id, "tier": tier, "owning_team": team, "team_members": members,
            "depends_on": deps, "depended_on_by": dependents,
            "docs": [{"id": i, "title": t, "author": a} for i, t, a in docs],
            "incidents": [{"id": i, "status": s, "summary": sm, "assignee": a} for i, s, sm, a in incidents]}


def save_message(tenant: str, conversation_id: str, role: str, text: str) -> None:
    """Persistent chat history: (:Conversation)-[:HAS_MESSAGE]->(:Message), kept in the tenant's graph."""
    clean_title = (text or "").strip()[:60] or "New Conversation"
    _rows(tenant, """
        MERGE (c:Conversation {id: $cid}) ON CREATE SET c.started = $ts, c.title = $title
        CREATE (c)-[:HAS_MESSAGE]->(:Message {role: $role, text: $text, ts: $ts})""",
          {"cid": conversation_id, "ts": datetime.now(timezone.utc).isoformat(), "title": clean_title,
           "role": role, "text": text})


def chat_history(tenant: str, conversation_id: str, limit: int = 20) -> list[dict]:
    rows = _rows(tenant, """MATCH (:Conversation {id: $cid})-[:HAS_MESSAGE]->(m:Message)
                            RETURN m.role, m.text ORDER BY m.ts DESC LIMIT $n""", {"cid": conversation_id, "n": limit})
    return [{"role": r, "content": t} for r, t in reversed(rows)]


def list_conversations(tenant: str) -> list[dict]:
    rows = _rows(tenant, "MATCH (c:Conversation) RETURN c.id, c.title, c.started ORDER BY c.started DESC LIMIT 50")
    return [{"id": i, "title": t, "started": s} for i, t, s in rows]


def delete_conversation(tenant: str, conversation_id: str) -> bool:
    """Delete a conversation and its messages from the graph."""
    _rows(tenant, """MATCH (c:Conversation {id: $cid})
                     OPTIONAL MATCH (c)-[:HAS_MESSAGE]->(m:Message)
                     DETACH DELETE c, m""", {"cid": conversation_id})
    return True


def list_all_runbooks(tenant: str) -> list[dict]:
    """List all available playbooks and their steps."""
    rows = _rows(tenant, "MATCH (p:Playbook) RETURN p.issue_type ORDER BY p.issue_type")
    return [get_runbook(tenant, r[0]) for r in rows]


def subgraph(tenant: str, service_id: str) -> dict:
    """Nodes/edges around a service for the UI: 2 hops of deps, owners, incidents, decisions."""
    rows = _rows(tenant, """
        MATCH (s:Service {id: $id})
        OPTIONAL MATCH p1 = (s)-[:DEPENDS_ON*1..2]-(:Service)
        OPTIONAL MATCH p2 = (s)-[:OWNS|AFFECTS|CHANGED]-()
        OPTIONAL MATCH p3 = (:Person)-[:ASSIGNED_TO]->(:Incident)-[:AFFECTS]->(s)
        RETURN collect(DISTINCT p1) + collect(DISTINCT p2) + collect(DISTINCT p3)""", {"id": service_id})
    nodes, edges = {}, set()
    for path in (rows[0][0] if rows else []):
        for n in path.nodes():
            nid = n.properties.get("id", str(n.id))
            nodes[n.id] = {"id": nid, "label": n.labels[0], "name": n.properties.get("name") or n.properties.get("title") or nid}
        for e in path.edges():
            edges.add((e.src_node, e.dest_node, e.relation))
    return {"nodes": list(nodes.values()),
            "edges": [{"source": nodes[a]["id"], "target": nodes[b]["id"], "type": r}
                      for a, b, r in edges if a in nodes and b in nodes]}
