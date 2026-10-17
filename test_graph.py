"""Self-check against a live FalkorDB (no LLM calls). Run: python test_graph.py"""
import seed
import tools

T = "selftest"
seed.build(T)

br = tools.get_blast_radius(T, "redis-cache")
names = {i["service"] for i in br["impacted"]}
assert {"rate-limiter", "api-gateway", "checkout"} <= names, names  # checkout is 3 hops up
assert "postgres-main" not in names  # not upstream of redis
assert tools.criticality(T)["redis-cache"] > tools.criticality(T)["checkout"]

ex = tools.find_expert_path(T, "auth-service", "auth_failure")
assert ex["owning_team"]["team"] == "identity"
assert all(e["evidence"] for e in ex["experts"])

assert [d["id"] for d in tools.decision_lineage(T, "redis-cache")] == ["DEC-5", "DEC-4"]
assert tools.decision_lineage(T, "redis-cache")[0]["supersedes"].startswith("Cap redis")

mem = tools.recall_memory(T, "auth-service", "auth_failure")
assert mem["episodes"] and len(mem["playbook"]) == 4

inc = tools.create_incident(T, "auth-service", "auth_failure", "401s", "vault TTL", ["p7"])["incident_id"]
assert tools.get_incident(T, inc)["status"] == "triaged"
assert tools.assign_incident(T, inc, "p7", ["rotate token"])["assigned_to"] == "Gus Moreno"
assert tools.get_incident(T, inc)["assignee"] == "Gus Moreno"
tools.assign_incident(T, inc, "p8", ["rotate token"])  # reassign replaces, not adds
assert tools.get_incident(T, inc)["assignee"] == "Hana Sato"
assert tools._rows(T, "MATCH ()-[r:ASSIGNED_TO]->(:Incident {id: $id}) RETURN count(r)", {"id": inc})[0][0] == 1
tools.log_episode(T, "S-test", "remediation", "auth-service", "auth_failure", "test episode")
assert len(tools.recall_memory(T, "auth-service", "auth_failure")["episodes"]) == 2

for bad in (lambda: tools.create_incident(T, "nope", "auth_failure", "x"),
            lambda: tools.log_episode(T, "S-bad", "remediation", "nope", "auth_failure", "x"),
            lambda: tools.get_incident(T, "INC-nope")):
    try:
        bad()
        raise AssertionError("expected ValueError for unknown id")
    except ValueError:
        pass
assert tools._rows(T, "MATCH (s:Session {id: 'S-bad'}) RETURN count(s)")[0][0] == 0  # no orphan session

hits = tools.search_knowledge(T, "who wrote the auth-service runbook")
assert "-DOCUMENTS-> auth-service" in hits[0]["links"], hits[:2]  # the runbook outranks the service itself
assert tools.search_knowledge(T, "a b") == []
ov = tools.service_overview(T, "auth-service")
assert ov["owning_team"] == "identity" and ov["docs"] and ov["incidents"][0]["id"] == inc
try:
    tools.service_overview(T, "nope")
    raise AssertionError("expected ValueError")
except ValueError:
    pass
tools.save_message(T, "C-test", "user", "first question")
tools.save_message(T, "C-test", "assistant", "first answer")
assert tools.chat_history(T, "C-test") == [{"role": "user", "content": "first question"},
                                          {"role": "assistant", "content": "first answer"}]
assert tools.list_conversations(T)[0]["title"] == "first question"

sg = tools.subgraph(T, "auth-service")
assert any(n["label"] == "Incident" for n in sg["nodes"]) and sg["edges"]

rb = tools.get_runbook(T, "latency")["steps"]
assert [s["id"] for s in rb] == ["R-latency-1", "R-latency-2", "R-latency-3", "R-latency-4"]
assert "DevOps" in rb[1]["if_fails"]["do"]
rb = tools.update_runbook(T, "latency", "set_fallback", "R-latency-2", "Drain traffic to region-b", "arch change", "Chen Wei")["steps"]
assert rb[1]["if_fails"]["do"] == "Drain traffic to region-b" and rb[1]["if_fails"]["changed_by"] == "Chen Wei"
assert tools._rows(T, "MATCH (r:ActionRule) WHERE r.text CONTAINS 'DevOps' AND (:ActionRule {id: 'R-latency-2'})-[:IF_FAILS]->(r) RETURN count(r)")[0][0] == 0
rb = tools.update_runbook(T, "latency", "insert_after", "R-latency-1", "Check connection pool")["steps"]
assert [s["do"] for s in rb][:3] == ["Check p99 on the service dashboard", "Check connection pool", "Check replica health on postgres-main"]
rb = tools.update_runbook(T, "latency", "remove", "R-latency-1")["steps"]
assert rb[0]["do"] == "Check connection pool" and len(rb) == 4
rb = tools.update_runbook(T, "latency", "remove", "R-latency-3")["steps"]
assert len(rb) == 3 and rb[-1]["id"] == "R-latency-4"  # middle removal relinks NEXT
assert tools.recall_memory(T, "postgres-main", "latency")["playbook"] == rb
for bad in [("R-auth_failure-1", "replace"), ("R-latency-2", "bogus"), ("R-latency-2", "replace")]:
    try:
        tools.update_runbook(T, "latency", bad[1], bad[0], "" if bad == ("R-latency-2", "replace") else "x")
        raise AssertionError(bad)
    except ValueError:
        pass

cust = tools.get_blast_radius(T, "postgres-main")["customers"]
assert cust and all(c["path"][0].startswith("C-") and c["path"][-1] == "postgres-main" for c in cust), cust
cmp = tools.compare_actions(T, "Restart postgres-main", ["postgres-main"], "Drain traffic to region-b", [], inc)
assert cmp["chosen"]["action"] == "Drain traffic to region-b" and cmp["rejected"]["vip_hit"], cmp
assert tools._rows(T, "MATCH (:DecisionReceipt {id: $r})-[:FOR]->(:Incident {id: $i}) RETURN count(*)",
                   {"r": cmp["receipt_id"], "i": inc})[0][0] == 1
# Empty string resilience test in compare_actions
cmp_resilient = tools.compare_actions(T, "Restart auth-service", ["auth-service", ""], "Drain traffic", [" "], inc)
assert cmp_resilient["chosen"]["action"] in ("Restart auth-service", "Drain traffic")

# Test conversation delete
tools.save_message(T, "C-del", "user", "to be deleted")
assert any(c["id"] == "C-del" for c in tools.list_conversations(T))
tools.delete_conversation(T, "C-del")
assert not any(c["id"] == "C-del" for c in tools.list_conversations(T))

# Test list_all_runbooks
all_rbs = tools.list_all_runbooks(T)
assert len(all_rbs) == 6
assert any(rb["issue_type"] == "latency" for rb in all_rbs)

assert tools._rows("selftest_other", "MATCH (n) RETURN count(n)")[0][0] == 0  # tenant isolation
tools.graph("selftest_other").delete()  # the read above creates an empty graph
tools.graph(T).delete()
print("all graph checks passed")
