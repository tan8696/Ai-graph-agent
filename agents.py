"""Two LLM agents (Gemini Flash, free tier) that coordinate through the graph, not through each other's context.

Triage agent:      alert -> blast radius, experts, recent decisions -> writes an Incident node.
Remediation agent: reads only the Incident id -> memory + playbook -> assigns, logs an Episode.

Run: python agents.py "auth-service is returning 401s for 30% of logins"
"""
import asyncio
import contextlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from typing import Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import tools  # also loads .env (GEMINI_API_KEY)

MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")  # Fast, reliable Gemini model
FALLBACK_MODELS = [MODEL, "gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"  # OpenAI-compatible endpoint
HERE = os.path.dirname(os.path.abspath(__file__))

TRIAGE_TOOLS = {"get_blast_radius", "find_expert_path", "decision_lineage", "recall_memory", "create_incident"}
REMEDIATION_TOOLS = {"get_incident", "recall_memory", "get_runbook", "find_expert_path", "compare_actions",
                     "assign_incident", "log_episode"}
CHAT_TOOLS = {"search_knowledge", "service_overview", "get_blast_radius", "find_expert_path", "decision_lineage",
              "recall_memory", "get_incident", "get_runbook", "update_runbook", "compare_actions"}
# chat never writes incidents; it may rewrite runbooks, but only when the user explicitly says so (see prompt)

TRIAGE_PROMPT = """You are the triage agent for a DevOps team. The company's services, people, tickets,
decisions and past incidents live in a graph you reach through tools.
Given an alert: identify the affected service id and issue type, measure the blast radius, find who has fixed
this before, and check recent decisions on the service for a likely cause. Then call create_incident exactly once
with a short summary, a suspected root cause, and 1-3 candidate assignee person ids.
Ground every claim in tool results. Finish with a two-sentence triage note."""

REMEDIATION_PROMPT = """You are the remediation agent. You receive only an incident id; read it from the graph.
Use past episodes and the playbook to write a concrete ordered plan (3-6 steps, adapted to this incident).
The playbook is a graph that operators rewrite: follow its steps in order and include each step's if_fails fallback
exactly as written, even if it differs from what you would expect. Before any disruptive step (restart, failover,
rollback), call compare_actions once with the incident id on that action versus the safest alternative
(e.g. reroute or drain traffic, which takes down no services) and put the chosen one in the plan. Then pick the single best assignee from the candidates (prefer someone with direct evidence on this service),
call assign_incident, then call log_episode with agent='remediation' and a one-line summary of what you decided.
Finish with a short handoff message to the assignee."""

CHAT_PROMPT = """You are the company brain for an engineering org. Everything you know (services, owners, people,
tickets, runbooks, architecture decisions, past incidents, agent episodes) lives in a graph you reach through tools.
If you do not know exact ids, call search_knowledge first, then follow the links it returns with the other tools.
Ground every claim in tool results and cite node ids in square brackets, e.g. [auth-service] [p7] [T-033] [DEC-3].
If the graph has no answer, say so plainly; never invent people, services or history.
Answer in short markdown (a few sentences or bullets). If the user describes a live outage or alert,
answer what you can and suggest switching to Incident mode so the triage and remediation agents take it.
Runbooks: when the user explicitly instructs a runbook change, call get_runbook, then update_runbook with the step ids
it returned (set_fallback for "if X fails do Y", replace/insert_after/remove otherwise), passing changed_by and reason
from the user's words. Show the new runbook afterwards. Never change a runbook unless explicitly told to.
"What if" questions about restarting or rerouting: call compare_actions and explain the chosen and rejected paths."""


def _chat(body: dict) -> dict:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("set GEMINI_API_KEY in .env (free key: https://aistudio.google.com/apikey)")
    
    models_to_try = [body.get("model", MODEL)]
    for fb in FALLBACK_MODELS:
        if fb not in models_to_try:
            models_to_try.append(fb)

    last_err = None
    for model_name in models_to_try:
        current_body = {**body, "model": model_name}
        req_data = json.dumps(current_body).encode()
        req = urllib.request.Request(URL, req_data,
                                     {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=90) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                err_text = e.read().decode(errors="replace")
                is_quota_exhausted = ("GenerateRequestsPerDay" in err_text or "RESOURCE_EXHAUSTED" in err_text)
                if e.code == 429 and not is_quota_exhausted and attempt < 3:
                    time.sleep(12)
                    continue
                if is_quota_exhausted or e.code == 404:
                    last_err = f"Gemini API {e.code} on {model_name}: {err_text[:300]}"
                    break  # try next fallback model
                raise RuntimeError(f"Gemini API {e.code}: {err_text[:500]}") from None
            except Exception as e:
                last_err = str(e)
                break
    raise RuntimeError(f"All Gemini models exhausted or unavailable: {last_err}")


async def run_agent(name: str, system: str, user: str, mcp: ClientSession, allowed: set[str],
                    emit: Callable[[dict], None], history: list[dict] = ()) -> list[dict]:
    """Manual tool loop over MCP tools. Returns every tool call made, for the caller to inspect."""
    tools = [{"type": "function", "function": {"name": t.name, "description": t.description,
                                               "parameters": t.input_schema}}
             for t in (await mcp.list_tools()).tools if t.name in allowed]
    messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": user}]
    calls = []
    for _ in range(15):  # hard cap on turns so a confused agent cannot loop forever
        choice = (await asyncio.to_thread(_chat, {"model": MODEL, "messages": messages, "tools": tools}))["choices"][0]
        if choice.get("finish_reason") == "length":
            raise RuntimeError(f"{name} agent: hit max tokens")
        msg = choice["message"]
        messages.append(msg)  # sent back as-is so Gemini's thought signatures survive
        if (msg.get("content") or "").strip():
            emit({"agent": name, "kind": "text", "text": msg["content"]})
        if not msg.get("tool_calls"):
            return calls

        for tc in msg["tool_calls"]:
            tool, args = tc["function"]["name"], json.loads(tc["function"]["arguments"] or "{}")
            emit({"agent": name, "kind": "tool_call", "tool": tool, "input": args})
            out = await mcp.call_tool(tool, args)
            text = "\n".join(c.text for c in out.content if c.type == "text")
            emit({"agent": name, "kind": "tool_result", "tool": tool, "output": text, "error": out.is_error})
            calls.append({"tool": tool, "input": args, "output": text, "error": out.is_error})
            # chat completions has no is_error field, so mark failures in the text the model reads
            messages.append({"role": "tool", "tool_call_id": tc["id"],
                             "content": f"ERROR: {text}" if out.is_error else text})
    raise RuntimeError(f"{name} agent: too many turns")


@contextlib.asynccontextmanager
async def _mcp(tenant: str):
    server = StdioServerParameters(command=sys.executable, args=[os.path.join(HERE, "mcp_server.py")],
                                   env={**os.environ, "TENANT": tenant}, cwd=HERE)
    async with stdio_client(server) as (r, w), ClientSession(r, w) as mcp:
        await mcp.initialize()
        yield mcp


async def run_chat(question: str, conversation_id: str, tenant: str = "acme",
                   emit: Callable[[dict], None] = print) -> str:
    """One chat turn. History is read from and written back to the graph, so conversations survive restarts."""
    history = tools.chat_history(tenant, conversation_id)
    tools.save_message(tenant, conversation_id, "user", question)
    texts = []
    async with _mcp(tenant) as mcp:
        await run_agent("brain", CHAT_PROMPT, question, mcp, CHAT_TOOLS,
                        lambda e: (texts.append(e["text"]) if e["kind"] == "text" else None, emit(e)), history)
    answer = texts[-1] if texts else "I could not find an answer in the graph."
    tools.save_message(tenant, conversation_id, "assistant", answer)
    emit({"agent": "system", "kind": "done", "answer": answer})
    return answer


async def run_incident(alert: str, tenant: str = "acme", emit: Callable[[dict], None] = print) -> dict:
    session_id = f"S-{uuid.uuid4().hex[:6]}"
    async with _mcp(tenant) as mcp:
        triage = await run_agent("triage", TRIAGE_PROMPT, f"Alert: {alert}", mcp, TRIAGE_TOOLS, emit)
        created = [c for c in triage if c["tool"] == "create_incident" and not c["error"]]
        if not created:
            raise RuntimeError("triage agent did not create an incident")
        incident_id = json.loads(created[-1]["output"])["incident_id"]
        emit({"agent": "system", "kind": "handoff", "incident_id": incident_id})
        await run_agent("remediation", REMEDIATION_PROMPT,
                        f"Incident id: {incident_id}. Session id: {session_id}.", mcp, REMEDIATION_TOOLS, emit)
        res = await mcp.call_tool("get_incident", {"incident_id": incident_id})
        if res.is_error:
            raise RuntimeError(res.content[0].text)
        final = json.loads(res.content[0].text)
    emit({"agent": "system", "kind": "done", "incident": final})
    return final


if __name__ == "__main__":
    alert = " ".join(sys.argv[1:]) or "auth-service is returning 401s for 30% of logins since 09:10"
    asyncio.run(run_incident(alert, emit=lambda e: print(json.dumps(e, default=str)[:400])))
