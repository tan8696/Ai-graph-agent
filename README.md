<div align="center">

# 🧠 Graph Brain

### Your company's memory, wired as a graph, run by agents.

**Paste an alert. In one run you get the blast radius, the right engineer, a fix that keeps VIP customers safe, and a signed decision receipt. Every step is a Cypher query against one FalkorDB graph.**

[![FalkorDB](https://img.shields.io/badge/Powered%20By-FalkorDB-red.svg)](https://www.falkordb.com/)
[![MCP](https://img.shields.io/badge/Protocol-Model%20Context%20Protocol-blue.svg)](https://modelcontextprotocol.io/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI%20%2B%20SSE-009688.svg)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-4285F4.svg)](https://ai.google.dev/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

### [🚀 Try the live demo](https://graphbrains.vercel.app) · [🎬 Watch the demo video](video/graph-brain-demo.mp4) · [⚡ Run it locally](#-run-it-in-3-commands)

<a href="https://graphbrains.vercel.app"><img src="docs/hero.png" alt="Graph Brain landing page with the incident pipeline simulation" width="900"></a>

**Entered in all three tracks:** Agents That Act on Connected Data · Agent Memory and Coordination · Company Brain

</div>

---

## 😩 The problem

When something breaks at 3 a.m., the answer to "what is affected, who knows how to fix it, and what changed?" is spread across a service catalog, an on-call sheet, old tickets, a wiki and someone's head. Engineers lose the first stretch of every incident just **finding context**, and the fix they choose can quietly hurt the one customer that matters most.

## 💡 The solution

Graph Brain puts all of that into **one company graph** in FalkorDB: teams, people, services, dependencies, tickets, decisions, customers and runbooks. Then it lets AI agents **act** on it over MCP:

- 🚨 **Triage agent:** walks the dependency graph for the blast radius, ranks services by PageRank, traces VIP customer paths and finds the engineer who already fixed this kind of issue.
- 🛠️ **Remediation agent:** picks the incident up *from the graph* (no shared context with Triage), recalls past episodes, pulls the runbook, simulates candidate actions against customer impact and signs a `DecisionReceipt`.
- 💬 **Ask Brain:** plain-English questions about any service, owner or past decision, answered with citation pills that light up the evidence in the graph.

## ⏱️ Judge this in 60 seconds

1. Open **[graphbrains.vercel.app](https://graphbrains.vercel.app)** and click **Open Console →**.
2. Switch to **Incident Triage** and paste: `auth-service is returning 401s for 30% of logins`
3. Watch Triage → handoff → Remediation stream live. The sandbox shows that **rotating the signing key hits 3 VIP customers, while rerouting to the fallback region hits none**, so it reroutes and records the receipt.
4. In **Ask Brain**, type: `If the replica check fails in the latency runbook, drain traffic to region-b instead.` The runbook is rewired as graph edges, live, with no redeploy.

## 🔁 Before vs. after

| Question during an incident | Without Graph Brain | With Graph Brain |
|---|---|---|
| What else breaks? | Read the service catalog by hand | `DEPENDS_ON*1..6` traversal + PageRank |
| Which customers feel it? Any VIPs? | Guess, or ask account managers | Shortest `Customer -USES-> … -DEPENDS_ON->` paths, VIPs flagged |
| Who should I page? | Whoever is on call | The engineer with `RESOLVED` tickets of this type nearby, with the path as proof |
| What changed recently? | Search Slack and wikis | `Decision -SUPERSEDES->` lineage on the service |
| Is the fix safe? | Hope | Counterfactual sandbox + signed `DecisionReceipt` |
| Update the runbook | Edit a doc nobody reads | Say it in chat, and the `NEXT` / `IF_FAILS` edges are rewired |

## ✨ Wow moments

- 🤝 **Two agents, zero shared context.** They coordinate only through the `(:Incident)` node's state machine in FalkorDB.
- 🧪 **Counterfactual sandbox.** Candidate actions are scored against VIP impact and PageRank risk *before* anything runs.
- 📝 **Self-editing runbooks.** Procedures are `FIRST` / `NEXT` / `IF_FAILS` chains, rewired from chat at runtime.
- 🧠 **Memory that lasts.** Conversations, episodes and procedures are graph nodes, so the brain remembers across sessions.
- 🏢 **Multi-tenant.** Each company gets its own isolated graph (`tenant_<name>`).
- 🔌 **13 MCP tools.** The agents reach data through nothing else.

---

## 🏆 How it maps to the tracks

| Track | What proves it |
|---|---|
| **1. Agents That Act on Connected Data** | Agents run multi-hop blast radius traversals (`DEPENDS_ON*1..6`), native PageRank (`algo.pageRank`), shortest VIP customer paths and evidence-backed expert routing, all over MCP. |
| **2. Agent Memory and Coordination** | Triage writes an `(:Incident)`; Remediation reads it from the graph and logs an `(:Episode)`. Three memory tiers: conversational (`Message`), episodic (`Episode`) and self-editing procedural (`Playbook → ActionRule` chains with fallback branches). |
| **3. Company Brain** | One graph holds ownership (`Team -OWNS-> Service`), decision lineage (`Decision -SUPERSEDES-> Decision`), runbooks, customers and incident memory, all queryable and editable from chat. |

## ⚡ Why the graph does the real work (Rule 3)

> *"The graph has to do real work. If the product still works once FalkorDB is taken out, the graph is decoration rather than the thing the product runs on."*

Take FalkorDB out and Graph Brain stops:

1. **Every MCP tool fails.** Each one in `tools.py` is a parameterized Cypher query.
2. **No blast radius.** Variable-length upstream traversal (`[:DEPENDS_ON*1..6]`) is a graph-native operation.
3. **No criticality.** Ranking comes from `CALL algo.pageRank('Service', 'DEPENDS_ON')`.
4. **No coordination.** The two agents share nothing in memory; the `(:Incident)` node is their only channel.
5. **No runbooks.** Procedures *are* edges (`:FIRST`, `:NEXT`, `:IF_FAILS`).
6. **No safety check.** The sandbox traverses `Customer -USES-> Service -DEPENDS_ON*0..4-> Target` to protect VIPs.

If the database is unreachable, the page shows a frozen read-only snapshot (`demo.py`) with a "DB unreachable" banner. Chat, incidents, runbooks, the inspector and every agent tool refuse to run without FalkorDB.

---

## 🏗️ How it works

```text
Alert ──▶ Triage agent ──MCP──▶ FalkorDB ◀──MCP── Remediation agent ──▶ Plan + DecisionReceipt
                │                  ▲                     │
                └── writes (:Incident) ──┘── reads it back ┘
```

<details>
<summary><b>Full multi-agent sequence diagram</b></summary>

```mermaid
sequenceDiagram
    autonumber
    actor User as Engineer / SRE
    participant Web as Web UI (index.html)
    participant API as FastAPI (app.py)
    participant Triage as Triage Agent
    participant Remediation as Remediation Agent
    participant MCP as MCP Server (mcp_server.py)
    participant Falkor as FalkorDB (tenant_acme)

    User->>Web: Paste alert: "auth-service returning 401s"
    Web->>API: GET /api/incident (SSE stream)
    API->>Triage: Run triage agent
    Triage->>MCP: get_blast_radius("auth-service")
    MCP->>Falkor: Cypher: DEPENDS_ON*1..6 + PageRank
    Falkor-->>MCP: Impacted services, VIP customers
    Triage->>MCP: find_expert_path & decision_lineage
    MCP->>Falkor: Cypher: Ticket resolvers & Decision chain
    Triage->>MCP: create_incident(...)
    MCP->>Falkor: CREATE (:Incident {status: 'triaged'})
    Falkor-->>API: SSE: event: handoff (incident_id: INC-c6775e)
    
    Note over API,Remediation: Decoupled Agent Handoff via FalkorDB
    
    API->>Remediation: Run remediation agent (INC-c6775e)
    Remediation->>MCP: get_incident("INC-c6775e")
    MCP->>Falkor: MATCH (i:Incident) RETURN i
    Remediation->>MCP: recall_memory & get_runbook
    MCP->>Falkor: MATCH (:Playbook)-[:FIRST]->(r:ActionRule)...
    Remediation->>MCP: compare_actions("Rotate signing key", "Reroute to fallback region")
    MCP->>Falkor: Counterfactual simulation (VIP safety check)
    Falkor-->>MCP: Chosen: Reroute (0 VIP hit vs 3 VIP hit)
    MCP->>Falkor: CREATE (:DecisionReceipt)-[:FOR]->(:Incident)
    Remediation->>MCP: assign_incident & log_episode
    MCP->>Falkor: MATCH (i), (p) CREATE (p)-[:ASSIGNED_TO]->(i)
    Remediation-->>API: Final Plan & Assignee
    API-->>Web: SSE: event: done (Incident assigned)
    Web-->>User: Render verified plan, receipt & evidence graph
```

</details>

<details>
<summary><b>Graph data model: 13 node labels, 14 relationship types</b></summary>

```mermaid
flowchart TD
    subgraph Organization ["🏢 Organizational Structure"]
        Team["Team<br/><i>id, name</i>"]
        Person["Person<br/><i>id, name, team</i>"]
        Person -- "MEMBER_OF" --> Team
        Team -- "OWNS" --> Service["Service<br/><i>id, tier</i>"]
    end

    subgraph Knowledge ["📚 Knowledge & Decisions"]
        Ticket["Ticket<br/><i>id, issue_type</i>"]
        Document["Document<br/><i>id, title</i>"]
        Decision["Decision<br/><i>id, title, date</i>"]
        
        Person -- "RESOLVED" --> Ticket
        Ticket -- "AFFECTS" --> Service
        Person -- "AUTHORED" --> Document
        Document -- "DOCUMENTS" --> Service
        Person -- "MADE" --> Decision
        Decision -- "CHANGED" --> Service
        Decision -- "SUPERSEDES" --> Decision
    end

    subgraph Topology ["🌐 Service Topology & Customers"]
        Customer["Customer<br/><i>id, name, vip</i>"]
        Service -- "DEPENDS_ON" --> Service
        Customer -- "USES" --> Service
    end

    subgraph MemoryCoordination ["🧠 Memory & Multi-Agent Coordination"]
        Incident["Incident<br/><i>id, status, plan, summary</i>"]
        Person -- "ASSIGNED_TO" --> Incident
        Incident -- "AFFECTS" --> Service
        DecisionReceipt["DecisionReceipt<br/><i>id, chosen, rejected, why</i>"]
        DecisionReceipt -- "FOR" --> Incident
        
        Session["Session<br/><i>id, started</i>"]
        Episode["Episode<br/><i>id, ts, agent, summary</i>"]
        Session -- "LOGGED_EVENT" --> Episode
        Episode -- "ABOUT" --> Service
        
        Conversation["Conversation<br/><i>id, title, started</i>"]
        Message["Message<br/><i>role, text, ts</i>"]
        Conversation -- "HAS_MESSAGE" --> Message
    end

    subgraph Procedural ["⚙️ Procedural Memory (Runbooks)"]
        Playbook["Playbook<br/><i>issue_type</i>"]
        ActionRule["ActionRule<br/><i>id, text, changed_by, reason</i>"]
        Playbook -- "FIRST" --> ActionRule
        ActionRule -- "NEXT" --> ActionRule
        ActionRule -- "IF_FAILS" --> ActionRule
    end
```

**Synthetic data (Rule 6):** `seed.py` deterministically generates a fictional company (`acme`) with 30 microservices, 15 engineers across 5 teams, 40 closed tickets, 6 architectural decisions, 5 customers and 6 incident playbooks. No private or proprietary data is loaded.

</details>

<details>
<summary><b>The 9 Cypher queries and graph algorithms behind it (<code>tools.py</code>)</b></summary>

### 1. PageRank Centrality (`criticality`)
Computes the structural importance of every service in the dependency graph so agents prioritize core infrastructure.
```cypher
CALL algo.pageRank('Service', 'DEPENDS_ON') YIELD node, score
RETURN node.id, score
```

### 2. Multi-Hop Blast Radius Traversal (`get_blast_radius`)
Evaluates variable-length upstream dependencies (up to 6 hops) to identify all cascading services and their owning teams when a service degrades.
```cypher
MATCH p = (up:Service)-[:DEPENDS_ON*1..$max_hops]->(s:Service {id: $id})
WITH up, min(length(p)) AS hops
OPTIONAL MATCH (t:Team)-[:OWNS]->(up)
RETURN up.id, up.tier, hops, t.id
ORDER BY hops, up.tier
```

### 3. Customer Impact & Shortest Path VIP Tracing (`_customer_paths`)
Finds all customers whose entry-point services depend on the degraded service, preserving shortest dependency paths as evidence and flagging VIP accounts.
```cypher
MATCH (d:Service) WHERE d.id IN $ids
MATCH p = (c:Customer)-[:USES]->(:Service)-[:DEPENDS_ON*0..4]->(d)
RETURN c.id, c.name, c.vip, [n IN nodes(p) | n.id], length(p) AS hops
ORDER BY hops
```

### 4. Expert Discovery with Resolution Evidence (`find_expert_path`)
Identifies engineers who have resolved the specific incident type on the target service or its immediate topological neighbors, returning full path evidence.
```cypher
MATCH (target:Service {id: $id})
MATCH (p:Person)-[:RESOLVED]->(t:Ticket {issue_type: $it})-[:AFFECTS]->(s:Service)
WHERE s = target OR (s)-[:DEPENDS_ON]-(target)
RETURN p.id, p.name, p.team, count(DISTINCT t) AS n,
       collect(DISTINCT p.name + ' -RESOLVED-> ' + t.id + ' -AFFECTS-> ' + s.id) AS paths
ORDER BY n DESC LIMIT 5
```

### 5. Architectural Decision Lineage (`decision_lineage`)
Traverses superseding decision chains to detect recent configuration adjustments or architectural changes that may explain root causes.
```cypher
MATCH (p:Person)-[:MADE]->(d:Decision)-[:CHANGED]->(:Service {id: $id})
OPTIONAL MATCH (d)-[:SUPERSEDES]->(old:Decision)
RETURN d.id, d.title, d.date, p.name, old.title
ORDER BY d.date DESC
```

### 6. Procedural Runbook Traversal (`get_runbook`)
Retrieves the ordered sequence of remediation actions and dynamically associated fallback steps (`-[:IF_FAILS]->`).
```cypher
MATCH (:Playbook {issue_type: $it})-[:FIRST]->(f:ActionRule)
MATCH p = (f)-[:NEXT*0..20]->(r:ActionRule)
OPTIONAL MATCH (r)-[:IF_FAILS]->(alt:ActionRule)
RETURN r.id, r.text, r.changed_by, r.reason, alt.id, alt.text, alt.changed_by, alt.reason, length(p) AS pos
ORDER BY pos
```

### 7. Self-Mutating Runbook Rewiring (`update_runbook`)
Allows operators to update, insert, remove, or attach fallback branches to runbook steps at runtime using atomic Cypher mutations:
```cypher
// Adding a fallback branch to a runbook step
MATCH (s:ActionRule {id: $sid})
CREATE (s)-[:IF_FAILS]->(:ActionRule {
    id: $nid,
    text: $text,
    changed_by: $by,
    reason: $why,
    updated: $now
})
```

### 8. Multi-Agent Incident Handoff (`create_incident` & `assign_incident`)
Enables the Triage Agent to persist findings in the graph, which the Remediation Agent subsequently consumes:
```cypher
// Triage agent creates handoff state
MATCH (s:Service {id: $sid})
CREATE (i:Incident {
    id: $iid,
    issue_type: $it,
    summary: $summary,
    root_cause: $rc,
    candidates: $cands,
    status: 'triaged',
    created: $now
})-[:AFFECTS]->(s)
RETURN i.id
```

### 9. Counterfactual Decision Receipts (`compare_actions`)
Compares candidate remediation actions (e.g., restart vs. drain) against customer impact and PageRank risk, writing an immutable receipt to the incident:
```cypher
MATCH (i:Incident {id: $iid})
CREATE (:DecisionReceipt {
    id: $rid,
    chosen: $c,
    rejected: $r,
    why: $why,
    ts: $now
})-[:FOR]->(i)
RETURN i.id
```

</details>

<details>
<summary><b>MCP tools and HTTP API</b></summary>

`mcp_server.py` exposes **13 graph tools** over the Model Context Protocol; the agents call nothing else to reach data.

| Tool | What it does |
|---|---|
| `get_blast_radius` | Upstream services, owners and VIP customers hit when a service degrades |
| `find_expert_path` | Engineers who resolved this issue type nearby, with path evidence |
| `decision_lineage` | Recent decisions on a service and what they superseded |
| `recall_memory` | Past episodes and incidents for a service + issue type |
| `search_knowledge` | Keyword search across the company graph |
| `service_overview` | Owner, tier, dependencies and customers of one service |
| `create_incident` / `get_incident` / `assign_incident` | The Triage → Remediation handoff state machine |
| `log_episode` | Writes episodic memory |
| `get_runbook` / `update_runbook` | Read and rewire procedural memory |
| `compare_actions` | Counterfactual sandbox that writes a `DecisionReceipt` |

| Endpoint | Purpose |
|---|---|
| `GET /api/chat` | Ask Brain (SSE stream) |
| `GET /api/incident` | Triage + Remediation pipeline (SSE stream) |
| `GET /api/services`, `/api/service/{id}`, `/api/graph/{id}` | Topology and subgraphs for the UI |
| `GET /api/runbooks` | Current runbook chains |
| `GET /api/conversations`, `/api/conversations/{cid}` | Stored chat memory |
| `GET /api/health`, `/healthz` | Health checks |

</details>

---

## 🚀 Run it in 3 commands

You need **Python 3.11+**, **Docker** (or a FalkorDB Cloud URL) and a free **[Gemini API key](https://aistudio.google.com/apikey)**.

```bash
git clone https://github.com/tan8696/Ai-graph-agent.git && cd Ai-graph-agent
docker compose up -d && pip install -r requirements.txt && cp .env.example .env   # then put GEMINI_API_KEY in .env
python seed.py && python test_graph.py && uvicorn app:app --reload               # open http://localhost:8000
```

`test_graph.py` should print `all graph checks passed`.

<details>
<summary><b>Step-by-step setup, FalkorDB Cloud and CLI agents</b></summary>

**1. Virtual environment (recommended)**

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
```

**2. FalkorDB:** `docker compose up -d` starts FalkorDB on port `6379` and its Browser UI on `3000`. For FalkorDB Cloud, put the connection URL in `.env` instead (URL-encode special characters in the password):

```ini
FALKORDB_URL=redis://user:password@your-falkordb-instance.falkordb.cloud:port
GEMINI_API_KEY=your_gemini_api_key_here
```

**3. Seed and test:** `python seed.py` builds the `acme` tenant. ⚠️ Re-running it wipes and rebuilds the tenant, including stored chat history. `python test_graph.py` checks every Cypher operation against the live graph without spending LLM tokens.

**4. Run the agents from the terminal:**

```bash
python agents.py "auth-service is returning 401s for 30% of logins"
```

</details>

<details>
<summary><b>What the test suite covers</b></summary>

`test_graph.py` provides an end-to-end regression test suite verifying all FalkorDB Cypher operations without consuming LLM tokens. It validates:
- **Blast Radius & Centrality**: Upstream dependency bounds, PageRank score ordering.
- **Evidence Path Attribution**: Resolver ticket link validity.
- **Decision Lineage**: Supersedes relation ordering (`DEC-5` -> `DEC-4`).
- **Memory & Procedural Mutation**: Runbook step addition, fallback creation, deletion with automatic `:NEXT` pointer reconciliation.
- **Counterfactual Action Sandbox**: Automated selection of safest action based on VIP customer protection and decision receipt attachment.
- **Multi-Tenant Isolation**: Complete data segregation between distinct tenant graphs.

</details>

---

## 🧗 Challenges we ran into

- **Agents that don't share memory still have to agree.** We made the `(:Incident)` node a small state machine (`triaged` → assigned) so the handoff is explicit and auditable.
- **"Safe" is a graph question.** A restart that looks harmless can sit on a VIP customer's path; the sandbox had to traverse `USES` + `DEPENDS_ON*0..4` before acting, not after.
- **Editing a linked list in Cypher.** Deleting a runbook step means reconnecting the `:NEXT` pointers around it atomically. `test_graph.py` covers it.
- **Staying up when the DB isn't.** A read-only snapshot keeps the page honest instead of blank, without pretending the agents still work.

## 🏅 Accomplishments we're proud of

- Two LLM agents coordinating **only** through graph state, live-streamed over SSE.
- Runbooks you can rewrite by talking to them, with the graph as the source of truth.
- Every agent claim is backed by a path you can click and see in the graph.
- A live multi-tenant deployment on FalkorDB Cloud.

## 📚 What we learned

- Graph traversals are the natural shape of operational questions: "what depends on this", "who fixed this nearby", "what did this decision replace".
- MCP is a clean boundary: the agents never touch the database directly, so every action is a named, testable tool.
- Storing memory as nodes and edges makes it inspectable, which matters as much as making it persistent.

## 🔭 What's next

- Ingest real signals (PagerDuty, GitHub, Slack) into the graph instead of seed data.
- Human-in-the-loop approval before the Remediation agent executes an action.
- Learn edge weights from incident outcomes so routing and the sandbox improve over time.

---

<details>
<summary><b>🛠️ Project structure</b></summary>

```text
ai-agent/
├── app.py                 # FastAPI web server, SSE streaming, and graph API endpoints
├── agents.py              # Autonomous LLM agents (Triage, Remediation, Chat) & MCP tool loop
├── mcp_server.py          # Model Context Protocol (MCP) stdio server exposing 13 graph tools
├── tools.py               # Pure Cypher implementation for all FalkorDB operations & algorithms
├── seed.py                # Synthetic company data generator (services, teams, runbooks, tickets)
├── test_graph.py          # Comprehensive Cypher & graph algorithm verification suite
├── demo.py                # Read-only graph snapshot shown only when FalkorDB is unreachable
├── static/
│   ├── index.html         # Single-page UI with Cytoscape.js graph visualizer and SSE chat
│   └── reactbits.js/.css  # Small UI effects (spotlight cards, text animations)
├── docker-compose.yml     # Official FalkorDB container configuration (ports 6379, 3000)
├── requirements.txt       # Python dependencies (falkordb, fastapi, uvicorn, mcp)
├── PROJECT.md             # In-depth architectural specification and system guide
└── README.md              # Submission overview, graph model, Cypher reference, and setup
```

</details>

## 🤖 AI coding assistant disclosure

- **Tools used:** Antigravity IDE, Google Gemini and Claude Code (Anthropic), for code drafting, Cypher syntax checks, test writing, UI styling, bug fixing and deployment hardening.
- **Our part:** the architecture, multi-agent coordination protocol, graph schema, counterfactual sandbox logic and procedural memory mutation were designed, verified and debugged by the team. All code has been tested and is understood by us.

More detail: [PROJECT.md](PROJECT.md) (architecture) · [DEMO_VIDEO.md](DEMO_VIDEO.md) (video script).

## ⚖️ License

MIT. See [LICENSE](LICENSE).
