"""Web UI: chat with the company brain, or fire an alert and watch the agents hand off through the graph.

Run: uvicorn app:app --reload   then open http://localhost:8000
"""
import asyncio
import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

import tools
from agents import run_chat, run_incident

app = FastAPI()
HERE = os.path.dirname(os.path.abspath(__file__))


def _tenant(t: str) -> str:
    if not t.isidentifier():  # tenant becomes part of a graph name
        raise HTTPException(400, "bad tenant")
    return t


@app.get("/")
def index():
    path = os.path.join(HERE, "static", "index.html")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(
        content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/api/services")
def services(tenant: str = "acme"):
    return [r[0] for r in tools._rows(_tenant(tenant), "MATCH (s:Service) RETURN s.id ORDER BY s.id")]


@app.get("/api/graph/{service_id}")
def graph(service_id: str, tenant: str = "acme"):
    return tools.subgraph(_tenant(tenant), service_id)


@app.get("/api/health")
def health(tenant: str = "acme"):
    t = _tenant(tenant)
    try:
        svc_count = len(tools._rows(t, "MATCH (s:Service) RETURN s.id"))
        from agents import MODEL
        return {"status": "ok", "tenant": t, "database": "connected", "services": svc_count, "model": MODEL}
    except Exception as e:
        return {"status": "degraded", "tenant": t, "error": str(e)}


@app.get("/api/conversations")
def conversations(tenant: str = "acme"):
    return tools.list_conversations(_tenant(tenant))


@app.get("/api/conversations/{cid}")
def conversation(cid: str, tenant: str = "acme"):
    return tools.chat_history(_tenant(tenant), cid, limit=200)


@app.delete("/api/conversations/{cid}")
def delete_conversation(cid: str, tenant: str = "acme"):
    tools.delete_conversation(_tenant(tenant), cid)
    return {"deleted": cid}


@app.get("/api/service/{service_id}")
def service_detail(service_id: str, tenant: str = "acme"):
    return tools.service_overview(_tenant(tenant), service_id)


@app.get("/api/runbooks")
def runbooks(tenant: str = "acme"):
    return tools.list_all_runbooks(_tenant(tenant))


def _incident_summary(inc: dict) -> str:
    plan = "\n".join(f"{i}. {step}" for i, step in enumerate(inc.get("plan") or [], 1))
    iid = inc.get("incident_id") or "UNKNOWN"
    svc = inc.get("service") or "unknown-service"
    assignee = inc.get("assignee") or "nobody"
    summary = inc.get("summary") or ""
    cause = inc.get("suspected_root_cause") or "unknown"
    return (f"**Incident [{iid}]** on [{svc}], assigned to **{assignee}**\n\n"
            f"{summary}\n\n**Suspected cause:** {cause}\n\n"
            f"**Remediation Plan:**\n{plan if plan else '_No explicit steps recorded_'}")


async def _incident_turn(alert: str, cid: str, tenant: str, emit) -> None:
    tools.save_message(tenant, cid, "user", alert)
    inc = await run_incident(alert, tenant, emit=emit)
    answer = _incident_summary(inc)
    tools.save_message(tenant, cid, "assistant", answer)
    emit({"agent": "system", "kind": "done", "answer": answer})


@app.get("/api/chat")
async def chat(message: str, conversation: str, mode: str = "ask", tenant: str = "acme"):
    """Server-sent events: one JSON event per agent step. mode=ask -> company-brain chat, mode=incident -> agents."""
    if not 0 < len(message) <= 4000 or not 0 < len(conversation) <= 64 or mode not in ("ask", "incident"):
        raise HTTPException(400, "bad request")
    tenant = _tenant(tenant)
    if mode == "ask":
        return _sse(lambda emit: run_chat(message, conversation, tenant, emit))
    return _sse(lambda emit: _incident_turn(message, conversation, tenant, emit))


@app.get("/api/incident")
async def incident(alert: str, tenant: str = "acme"):
    tenant = _tenant(tenant)
    return _sse(lambda emit: run_incident(alert, tenant, emit=emit))


def _sse(job) -> StreamingResponse:
    q: asyncio.Queue = asyncio.Queue()

    async def worker():
        try:
            await job(q.put_nowait)
        except Exception as e:
            while hasattr(e, "exceptions") and e.exceptions:  # Unwrap TaskGroup / ExceptionGroup
                e = e.exceptions[0]
            q.put_nowait({"agent": "system", "kind": "error", "text": str(e)})
        q.put_nowait(None)

    async def stream():
        task = asyncio.create_task(worker())
        try:
            while (ev := await q.get()) is not None:
                yield f"data: {json.dumps(ev, default=str)}\n\n"
        finally:
            task.cancel()  # client went away

    return StreamingResponse(stream(), media_type="text/event-stream")
