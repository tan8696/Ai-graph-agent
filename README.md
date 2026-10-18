<div align="center">

# 🧠 Graph Brain

### The autonomous DevOps knowledge engine that runs on a graph

**Paste an alert. Get the blast radius, the right engineer, a VIP-safe fix and a signed decision receipt — all traced through one company graph in FalkorDB.**

[![FalkorDB](https://img.shields.io/badge/Powered%20By-FalkorDB-red.svg)](https://www.falkordb.com/)
[![MCP](https://img.shields.io/badge/Protocol-Model%20Context%20Protocol-blue.svg)](https://modelcontextprotocol.io/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI%20%2B%20SSE-009688.svg)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-4285F4.svg)](https://ai.google.dev/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**[🚀 Live demo](https://graphbrains.vercel.app)** · **[📖 Architecture](PROJECT.md)** · **[🎬 Demo script](DEMO_VIDEO.md)** · **[⚡ Quickstart](#-quickstart--setup-guide)**

</div>

---

## ✨ Highlights

- 💬 **Ask Brain** — ask about any service, owner or past decision in plain English; every answer comes with clickable citation pills that focus the evidence graph.
- 🚨 **Incident triage in seconds** — blast radius over `DEPENDS_ON*1..6`, PageRank criticality, VIP customer paths and the best-qualified engineer, from one alert.
- 🤝 **Two agents, zero shared context** — a Triage agent writes an `(:Incident)` node; a Remediation agent picks it up from the graph and finishes the job.
- 🧪 **Counterfactual sandbox** — compares candidate actions against customer impact before acting, and records the choice as a `(:DecisionReceipt)`.
- 📝 **Runbooks are graph edges** — `FIRST` / `NEXT` / `IF_FAILS` chains you can rewrite from chat, live, without a redeploy.
- 🧠 **Memory that lasts** — conversations, episodes and procedures are stored as graph nodes, so the brain remembers across sessions.
- 🏢 **Multi-tenant** — each company gets its own isolated FalkorDB graph (`tenant_<name>`).

| Submission | Link |
|---|---|
| **Live deployment** | https://graphbrains.vercel.app (FalkorDB Cloud + Gemini) |
| **Source code** | https://github.com/tan8696/Ai-graph-agent |
| **Demo video** | Script and scene plan in [DEMO_VIDEO.md](DEMO_VIDEO.md) |
| **Tracks** | Agents That Act on Connected Data · Agent Memory and Coordination · Company Brain |

### 📑 Contents

[Tracks](#-hackathon-tracks-entered) · [Why FalkorDB](#-why-falkordb-is-indispensable-proof-of-real-work) · [Data model](#️-graph-data-model) · [Cypher](#-cypher-queries--graph-algorithms) · [Architecture](#️-architecture--multi-agent-flow) · [MCP tools](#-mcp-tools--http-api) · [Quickstart](#-quickstart--setup-guide) · [Tests](#-graph-verification-test-suite-test_graphpy) · [Structure](#️-project-structure)

---

## 🏆 Hackathon Tracks Entered

This project is submitted to **all three hackathon tracks**:

| Track | Implementation & Proof in Graph Brain |
|---|---|
| **1. Agents That Act on Connected Data** | Autonomous agents execute complex graph analytics over FalkorDB via the Model Context Protocol (MCP): multi-hop upstream blast radius traversals (`DEPENDS_ON*1..6`), native PageRank criticality scoring (`algo.pageRank`), shortest customer impact paths with VIP risk analysis, and expert routing using historical resolution paths as evidence. |
| **2. Agent Memory and Coordination** | Multi-agent coordination with **zero direct context sharing**. The **Triage Agent** diagnoses alerts and writes an `(:Incident)` node into FalkorDB; the **Remediation Agent** wakes up, reads the incident from the graph, evaluates counterfactual sandbox scenarios, and logs an `(:Episode)`. Features three tiers of graph-native memory: Conversational (`Message`), Episodic (`Episode`), and Self-Mutating Procedural (`Playbook` -> `ActionRule` chains with dynamic fallback branches). |
| **3. Company Brain** | A single unified organizational brain consolidating team ownership (`Team -OWNS-> Service`), decision lineage (`Decision -SUPERSEDES-> Decision`), runbooks, customer relationships, and incident memory. Natural language interactions allow engineers to query institutional knowledge or mutate procedural runbooks directly from chat with live graph updates. |

---

## ⚡ Why FalkorDB is Indispensable (Proof of Real Work)

> **Hackathon Rule 3 Compliance:** *“The graph has to do real work. If the product still works once FalkorDB is taken out, the graph is decoration rather than the thing the product runs on.”*

In Graph Brain, **the graph is not a visualization layer — it is the primary execution engine**. If FalkorDB is removed:
1. **The MCP Server immediately crashes**: Every tool in `tools.py` directly executes parameterized Cypher queries against FalkorDB.
2. **Blast Radius Analysis Fails**: Relational or document stores cannot compute recursive, variable-length upstream dependency traversals (`[:DEPENDS_ON*1..6]`) with cycle detection and sub-millisecond response times.
3. **Graph Centrality is Impossible**: Service criticality rankings rely directly on FalkorDB's native graph algorithm library (`CALL algo.pageRank('Service', 'DEPENDS_ON')`).
4. **Agent Coordination Halts**: The Triage and Remediation agents have separate LLM context windows and share no state in memory. They coordinate **exclusively** through the state machine of the `(:Incident)` node in FalkorDB.
5. **Procedural Memory Mutation Breaks**: Runbooks are stored as physical graph edges (`:FIRST`, `:NEXT`, `:IF_FAILS`). Operators rewrite remediation procedures at runtime by re-wiring graph edges without redeploying code.
6. **Counterfactual Safety Fails**: The pre-flight action sandbox traverses customer-to-service paths (`Customer -USES-> Service -DEPENDS_ON*0..4-> Target`) to protect VIP clients before destructive actions (like service restarts) are executed.

If the database is unreachable, the web page shows a frozen read-only snapshot of the graph (`demo.py`) with a "DB unreachable" banner, so visitors see an explanation instead of a blank page. Chat, incidents, runbooks, the inspector and every agent tool need FalkorDB and refuse to run without it.

---

## 🗺️ Graph Data Model

The company graph consists of **13 node labels** and **14 relationship types**, representing the entire operational fabric of an engineering organization.

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

### Data Compliance Note
In strict accordance with Hackathon Rule 6, **all data used in this project is 100% synthetic**. The seed script (`seed.py`) deterministically generates a fictional technology company (`acme`) with 30 microservices, 15 engineers across 5 teams, 40 closed tickets, 6 architectural decisions, 5 customer tiers, and 6 active incident playbooks. No private, confidential, or proprietary data is loaded.

---

## 🔍 Cypher Queries & Graph Algorithms

Below are the primary Cypher queries and graph algorithms driving Graph Brain (`tools.py`):

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

---

## 🏗️ Architecture & Multi-Agent Flow

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

---

## 🔌 MCP Tools & HTTP API

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

---

## 🚀 Quickstart & Setup Guide

### Prerequisites
- **Python 3.11+**
- **Docker** (for local FalkorDB) *OR* a **FalkorDB Cloud** account
- **Google Gemini API Key** ([Get free key from Google AI Studio](https://aistudio.google.com/apikey))

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/tan8696/Ai-graph-agent.git
cd Ai-graph-agent
```

---

### Step 2: Start FalkorDB

#### Option A: Local Docker (Recommended)
```bash
docker compose up -d
```
*This starts FalkorDB on port `6379` and the FalkorDB Browser UI on port `3000`.*

#### Option B: FalkorDB Cloud
If using FalkorDB Cloud, copy the Redis connection URL into your `.env` file:
```ini
FALKORDB_URL=redis://user:password@your-falkordb-instance.falkordb.cloud:port
```
*(Tip: URL-encode any special characters in the password).*

---

### Step 3: Install Dependencies
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (cmd/PowerShell):
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env` and set your free Gemini API key:
```bash
cp .env.example .env
```
Inside `.env`:
```ini
FALKORDB_URL=redis://localhost:6379
GEMINI_API_KEY=your_gemini_api_key_here
```

---

### Step 5: Seed the Graph & Run Test Suite
```bash
# Seed the synthetic tenant company graph (acme)
# ⚠️ Re-running wipes and rebuilds the tenant, including stored chat history
python seed.py

# Run graph verification test suite (validates all Cypher queries against live FalkorDB)
python test_graph.py
```
**Expected test suite output:**
```text
all graph checks passed
```

---

### Step 6: Launch the Web Application
```bash
uvicorn app:app --reload
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

### Step 7: (Optional) Run CLI Agents Directly
You can run the multi-agent incident pipeline directly from your terminal:
```bash
python agents.py "auth-service is returning 401s for 30% of logins"
```

---

## 🧪 Graph Verification Test Suite (`test_graph.py`)

`test_graph.py` provides an end-to-end regression test suite verifying all FalkorDB Cypher operations without consuming LLM tokens. It validates:
- **Blast Radius & Centrality**: Upstream dependency bounds, PageRank score ordering.
- **Evidence Path Attribution**: Resolver ticket link validity.
- **Decision Lineage**: Supersedes relation ordering (`DEC-5` -> `DEC-4`).
- **Memory & Procedural Mutation**: Runbook step addition, fallback creation, deletion with automatic `:NEXT` pointer reconciliation.
- **Counterfactual Action Sandbox**: Automated selection of safest action based on VIP customer protection and decision receipt attachment.
- **Multi-Tenant Isolation**: Complete data segregation between distinct tenant graphs.

---

## 🎥 Demo Walkthrough

A 2½-minute tour (full script in [DEMO_VIDEO.md](DEMO_VIDEO.md)):

1. **Ask Brain** — *"Who should I page for auth-service and what changed recently?"* The agent queries FalkorDB over MCP and answers with citation pills (`[p7]`, `[DEC-3]`) that focus the evidence graph.
2. **Incident mode** — *"auth-service is returning 401s for 30% of logins."* Triage traces the blast radius, ranks by PageRank and writes an `(:Incident)` node.
3. **Handoff** — the Remediation agent reads that incident from the graph, recalls past episodes and pulls the runbook.
4. **Sandbox** — rotating the signing key would hit 3 VIP customers; rerouting to the fallback auth region hits none. It picks the reroute, records a `DecisionReceipt` and assigns the on-call engineer.
5. **Self-editing runbook** — *"If the replica check fails in the latency runbook, drain traffic to region-b instead."* `update_runbook` rewires the graph live.

---

## 🛠️ Project Structure

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

---

## 🤖 AI Coding Assistant Disclosure

In full compliance with Hackathon rules:
- **AI Coding Assistants Used**: Antigravity IDE, Google Gemini and Claude Code (Anthropic) were used for code drafting, Cypher syntax checks, test writing, UI styling, bug fixing and deployment hardening.
- **Participant Contribution & Understanding**: The system architecture, multi-agent coordination protocol, graph schema design, counterfactual sandbox logic, and procedural memory mutation algorithms were designed, verified, and debugged by the human team. All code has been thoroughly tested, analyzed, and understood.

---

## ⚖️ License

Distributed under the MIT License. See `LICENSE` for more information.
