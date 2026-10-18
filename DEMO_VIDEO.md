# Graph Brain: Demo Video Plan

This file is the plan for the demo video. The video must do one job: prove that FalkorDB is doing the real work. A judge should see the graph model, a live answer with sources, two agents handing off through a graph node, a runbook changing from chat, memory that survives a reload, and the same data sitting in FalkorDB Cloud. Target length is under 3 minutes.

Live site: https://graphbrains.vercel.app
Repo: https://github.com/tan8696/Ai-graph-agent

---

## 1. What the hackathon requires

Facts from the WeMakeDevs "Graph Hacks: Context for AI Agents" site:

- **Rule 10.** Every submission needs: a public source-code repository; a README with setup instructions and the graph data model; the Cypher queries or graph algorithms the product depends on; a demo video showing the working project; a live deployment (or complete local setup instructions); the track(s) entered.
- **Rule 3.** "The graph has to do real work... if the product still works once FalkorDB is taken out, the graph is decoration."
- **Rule 12.** Participants must be able to explain the graph model, queries, architecture and decisions. The narration should cover these briefly.
- **Rule 11.** AI coding assistant use must be disclosed. It is in the README. Repeat it in the video description.
- **Judges look for** (challenge page, "Work the graph has to do"): follow connections across data, remember across sessions, share state between agents, connect people, projects and decisions, show the path behind an answer.
- **Tracks entered: all three.**
  1. Agents That Act on Connected Data
  2. Agent Memory and Coordination
  3. Company Brain
- **Deadline:** Oct 18 2026, 11:59 PM IST.

**The site gives no required length, resolution or hosting platform for the video.** The table below is our own recommendation, not a rule.

| Item | Our recommendation |
|---|---|
| Length | 2:30 to 3:00 |
| Resolution | 1080p (1920x1080) |
| Aspect ratio | 16:9 |
| Audio | Screen recording with your own voiceover. No music, or very quiet music. |
| Platform | YouTube, or Loom |
| Visibility | YouTube "Unlisted". The link must open for anyone, with no login. |
| File fallback | Keep the .mp4 locally. If the form accepts an upload, use it. |

---

## 2. Must-show checklist

- [ ] Live URL `graphbrains.vercel.app` visible in the address bar the whole time (Rule 10, live deployment)
- [ ] Graph data model: node types and edges named, with the Evidence Graph on screen (Rule 10, Rule 12)
- [ ] Ask Brain answer with citations; click a citation pill to focus the graph (Track 3, answers with sources; judges: show the path behind an answer)
- [ ] Multi-hop blast radius (`DEPENDS_ON*1..6`) and PageRank shown in the triage tool calls (Track 1, multi-hop reasoning and graph algorithms as agent tools)
- [ ] Triage to remediation handoff through the `(:Incident)` node, with the handoff event visible (Track 2, shared state and handoffs)
- [ ] Counterfactual sandbox (`compare_actions`, restart vs drain) and the DecisionReceipt (Track 1, actions based on the graph, explainable results)
- [ ] Runbook change from chat, then the Runbooks tab showing the new fallback (Track 2, procedural memory; Track 3, keeping knowledge current)
- [ ] Conversation still in the sidebar after a page reload (Track 2, persistent conversation history, memory across sessions)
- [ ] Per-tenant isolation: point at the `tenant: acme` label in the header and say each tenant is its own graph, `tenant_acme` (Track 2, separate memory per tenant)
- [ ] Proof in FalkorDB Cloud: run a Cypher query in the browser and show the incident or receipt the agents just created (Rule 3)
- [ ] All three track names on screen at the end (Rule 5)

---

## 3. Before you hit record

- [ ] Run every prompt in section 4 once, a few minutes before recording. This warms the serverless function and shows you what Gemini answers. A cold start plus Gemini can take several seconds per step.
- [ ] Open the site fresh. On the Console view click **+ New Session** so the thread is empty.
- [ ] The sidebar may hold old test chats such as "judgetest1", "livecheck2" and "what is photosynthesis". They show in the video. Avoid scrolling the sidebar, or clean them up first. Do not re-seed the tenant: `seed.py` wipes all chat history.
- [ ] Close other tabs, silence notifications, turn on Do Not Disturb.
- [ ] Browser zoom about 110%. Hide the bookmarks bar. Keep the address bar visible.
- [ ] Open a second tab with the FalkorDB Cloud browser, logged in, with graph `tenant_acme` selected. Test one query so the page is warm.
- [ ] Test the mic. Record 10 seconds and listen back.
- [ ] OBS: canvas and output 1920x1080, 30 fps, record to mp4 or mkv (mkv survives crashes; remux to mp4 after).
- [ ] If an LLM step is slow, cut the wait in editing. Do not re-record. A speed-up of the waiting part also works.
- [ ] Do not show API keys, the Redis URL or the FalkorDB password. Use the browser tab, not the `.env` file.

---

## 4. Shot-by-shot script (about 2:50)

Use only the real UI labels. Type prompts exactly as written. Start on the **Overview** view with the address bar visible.

| Time | On screen and exact actions | Voiceover |
|---|---|---|
| 0:00 to 0:15 | Landing page "The Company Knowledge Graph for Autonomous DevOps." Let the incident stream card play. | "What breaks if auth-service goes down? Who do I page? Why was it built this way? The answers to these questions live in relationships, not rows. This is Graph Brain, built on FalkorDB." |
| 0:15 to 0:35 | Click **Open Agent Console**. Console opens with the **Evidence Graph** tab. Point at the graph and at the header label `tenant: acme`. Optionally click **FORCE**, **HIERARCHY**, **RADIAL** once each. | "One company, one graph. Nodes are Service, Team, Person, Ticket, Decision, Customer, Incident, Playbook and ActionRule, Episode, DecisionReceipt and Message. Edges are DEPENDS_ON, OWNS, MEMBER_OF, RESOLVED, SUPERSEDES, USES, and FIRST, NEXT and IF_FAILS for runbooks. Each tenant gets its own graph in FalkorDB Cloud." |
| 0:35 to 1:05 | Click **+ New Session**. Make sure **Ask Brain** is selected. Type: `Who should I page for auth-service, and what architecture decisions shaped it?` Press Enter. Let tool calls stream. When the answer shows citation pills such as `[p7]` or `[DEC-3]`, click one. The graph focuses on that node. | "This is Ask Brain, the company brain. The agent picks graph tools over MCP and runs Cypher in FalkorDB. Every claim carries a citation. I click one, and the graph shows the exact path behind the answer: person, ticket, service." |
| 1:05 to 1:55 | Click **Incident Triage**. Type: `auth-service is returning 401 errors for 30% of logins` and send. Narrate as steps appear: blast radius and PageRank tool calls, expert and decision lookups, then the **handoff** event, then runbook, `compare_actions`, receipt, assignee. Show the evidence graph with the chosen path (green) and rejected path (red). | "Now an alert. The triage agent runs a multi-hop blast radius over DEPENDS_ON up to six hops, plus PageRank, through MCP tools. It writes an Incident node. Watch the handoff. The remediation agent has its own context and never sees the triage prompt. It reads the incident from the graph, recalls the runbook, then runs a sandbox: restart versus traffic drain. Restart hits VIP customers, drain does not. It picks drain, writes a DecisionReceipt, and assigns an engineer with ticket evidence." |
| 1:55 to 2:20 | Switch back to **Ask Brain**. Type: `If the replica check fails in the latency runbook, drain traffic to region-b instead` and send. When it finishes, click the **Runbooks** tab and show the latency runbook with the new fallback. | "Runbooks are graph edges, not text. I ask in plain English. The agent calls update_runbook and rewires an IF_FAILS edge. Here in the Runbooks tab is the new fallback. The next incident follows it with no code change." |
| 2:20 to 2:35 | Press F5 to reload. Click **Open Agent Console** if the landing page shows (URL hash `#console` also works). Open the conversation in the sidebar. | "Memory survives the reload. Every message is a node in the graph, so the conversation is still here. This is memory across sessions, per tenant." |
| 2:35 to 2:50 | Switch to the FalkorDB Cloud tab, graph `tenant_acme`. Paste and run Query 1 (below). Show the incident row with the assignee. Optionally run Query 3 for the receipt. | "Here is the proof. This is FalkorDB Cloud. The incident the agents just wrote, with its assignee and status. Take FalkorDB away and none of this works. The agents only coordinate through these nodes." |
| 2:50 to 3:00 | Back to the app tab. Show the address bar and, if you can, a closing card (see below). | "Graph Brain. Live at graphbrains dot vercel dot app. Source on GitHub. Entered in all three tracks." |

Closing card text (add in editing): `graphbrains.vercel.app`, `github.com/tan8696/Ai-graph-agent`, `Tracks: Agents That Act on Connected Data · Agent Memory and Coordination · Company Brain`.

### Cypher for the FalkorDB Cloud tab (matches the real schema)

Query 1, latest incidents with assignee:

```cypher
MATCH (i:Incident)-[:AFFECTS]->(s:Service)
OPTIONAL MATCH (p:Person)-[:ASSIGNED_TO]->(i)
RETURN i.id, i.status, i.issue_type, s.id, p.name
ORDER BY i.created DESC LIMIT 5
```

Query 2, a runbook chain with fallbacks:

```cypher
MATCH (:Playbook {issue_type: 'latency'})-[:FIRST]->(f:ActionRule)
MATCH p = (f)-[:NEXT*0..20]->(r:ActionRule)
OPTIONAL MATCH (r)-[:IF_FAILS]->(alt:ActionRule)
RETURN r.id, r.text, alt.id, alt.text, alt.changed_by, length(p) AS pos
ORDER BY pos
```

Query 3, decision receipts:

```cypher
MATCH (d:DecisionReceipt)-[:FOR]->(i:Incident)
RETURN i.id, d.chosen, d.rejected, d.why
ORDER BY d.ts DESC LIMIT 5
```

If a graph view is nicer than a table, use `RETURN i, s, p` in Query 1 so the browser draws the nodes.

---

## 5. Full voiceover script (about 400 words)

What breaks if auth-service goes down? Who do I page? Why was it built this way? Those answers live in relationships, not rows. This is Graph Brain, built on FalkorDB.

One company, one graph. The nodes are Service, Team, Person, Ticket, Decision, Customer, Incident, Playbook and ActionRule, Episode, DecisionReceipt and Message. The edges are DEPENDS_ON, OWNS, MEMBER_OF, RESOLVED, SUPERSEDES, USES, and FIRST, NEXT and IF_FAILS for runbooks. Each tenant gets its own graph in FalkorDB Cloud.

This is Ask Brain, the company brain. The agent picks graph tools over MCP and runs Cypher in FalkorDB. Every claim carries a citation. I click one, and the graph shows the exact path behind the answer: the person, the ticket, the service.

Now an alert. The triage agent runs a multi-hop blast radius over DEPENDS_ON, up to six hops, and PageRank, through MCP tools. It finds who resolved similar tickets and which decisions changed the service. Then it writes an Incident node into the graph.

Watch the handoff. The remediation agent has its own context. It never sees the triage prompt. It reads the incident from the graph, recalls the runbook, and runs a sandbox: restart versus traffic drain. Restart would hit VIP customers. Drain would not. So it picks drain, writes a DecisionReceipt, and assigns one engineer, with ticket evidence behind the choice.

Runbooks are graph edges, not text. I ask in plain English. The agent calls update_runbook and rewires an IF_FAILS edge. In the Runbooks tab, the new fallback is there. The next incident follows it with no code change.

Memory survives the reload. Every message is a node in the graph, so the conversation is still here. That is memory across sessions, kept per tenant.

Here is the proof. This is FalkorDB Cloud. The incident the agents just wrote, with its status and assignee. Take FalkorDB away and none of this works. The agents only coordinate through these nodes.

Graph Brain is live at graphbrains dot vercel dot app, and the source is on GitHub. It is entered in all three tracks: Agents That Act on Connected Data, Agent Memory and Coordination, and Company Brain.

---

## 6. The 60-second cut

For social posts or as a backup. Keep these scenes, with shortened lines:

| Time | Keep | Line |
|---|---|---|
| 0:00 to 0:08 | Hook on the landing page | "What breaks if auth-service goes down? Who do I page? The answers live in relationships. This is Graph Brain, on FalkorDB." |
| 0:08 to 0:18 | Evidence Graph, name the node types | "One company graph. Services, teams, people, tickets, decisions, customers, runbooks." |
| 0:18 to 0:45 | Incident Triage prompt, handoff, sandbox, receipt (trim waiting) | "A triage agent measures blast radius and PageRank, then writes an Incident node. A second agent reads it from the graph, tests restart against drain, protects the VIP customers, and assigns an engineer." |
| 0:45 to 0:55 | FalkorDB Cloud Query 1 | "Here is that node in FalkorDB Cloud. No FalkorDB, no coordination." |
| 0:55 to 1:00 | Closing card | "Graph Brain. Three tracks. Link below." |

Cut: the Ask Brain scene, the runbook edit, the reload. Say in the description that the full version has them.

---

## 7. Upload and submit

**Title suggestion:**
`Graph Brain: Multi-Agent DevOps Knowledge Engine on FalkorDB (Graph Hacks)`

**Description (paste as is):**

```text
Graph Brain is a multi-agent DevOps knowledge engine built on FalkorDB. Services, teams, people, tickets, decisions, customers, runbooks, incidents and chat history live in one graph per tenant. Two agents (triage and remediation) coordinate only through an Incident node in the graph, with no shared LLM context.

What the video shows:
- Ask Brain answers with citations that focus the evidence graph
- Multi-hop blast radius (DEPENDS_ON*1..6) and PageRank as MCP tools
- Triage to remediation handoff through the graph
- Counterfactual sandbox (restart vs drain) with a DecisionReceipt
- Runbooks rewired from chat (FIRST / NEXT / IF_FAILS edges)
- Conversation memory that survives a reload
- The same nodes queried live in FalkorDB Cloud

Live demo: https://graphbrains.vercel.app
Source: https://github.com/tan8696/Ai-graph-agent

Tracks: Agents That Act on Connected Data, Agent Memory and Coordination, Company Brain.

Tech: FalkorDB Cloud, Google Gemini, Model Context Protocol (MCP), FastAPI, Cytoscape.js.

Data: all data is synthetic.

AI assistant disclosure: Antigravity IDE, Google Gemini and Claude Code were used for code drafting, Cypher syntax checks, tests, UI styling and bug fixing. The architecture, graph schema and agent protocol were designed and verified by the team.

Built for the WeMakeDevs "Graph Hacks: Context for AI Agents" hackathon.
```

**Steps:**

1. Export the video as mp4, 1080p.
2. Upload to YouTube (or Loom). Set visibility to **Unlisted**. Paste the title and description above.
3. Open the link in a private window to confirm it plays without login.
4. In `README.md`, replace `_TODO: add video link_` in the submission table with the video link. Commit and push.
5. Open the WeMakeDevs submission panel. Add the repo link, the live URL and the video link. Name **all three tracks**.
6. Submit before Oct 18 2026, 11:59 PM IST.
