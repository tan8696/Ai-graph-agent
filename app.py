"""Web UI: chat with the company brain, or fire an alert and watch the agents hand off through the graph.

Run: uvicorn app:app --reload   then open http://localhost:8000
"""
import asyncio
import json
import os

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from redis.exceptions import ConnectionError as DBConnectionError, TimeoutError as DBTimeoutError
from fastapi.staticfiles import StaticFiles

import demo
import seed
import tools
from agents import run_chat, run_incident

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1024)
HERE = os.path.dirname(os.path.abspath(__file__))


@app.middleware("http")
async def security_headers(request, call_next):
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    return resp


@app.exception_handler(DBConnectionError)
@app.exception_handler(DBTimeoutError)
async def db_unreachable(request, exc):
    # FalkorDB down or FALKORDB_URL unset: a clear 503 instead of a bare 500
    return JSONResponse({"detail": "Graph database unreachable. Set FALKORDB_URL."}, status_code=503)


# Caps on the Gemini-backed endpoints. Counted in FalkorDB (it speaks Redis) so all instances share them.
PER_IP_HOURLY = int(os.environ.get("RATE_LIMIT_PER_IP_HOUR", "10"))
GLOBAL_DAILY = int(os.environ.get("RATE_LIMIT_GLOBAL_DAY", "300"))


def _over_limit(request: Request) -> str | None:
    # Vercel overwrites X-Forwarded-For with the real client IP; behind other proxies it can be spoofed.
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() or getattr(request.client, "host", "unknown")
    r = tools._db().connection
    for key, ttl, cap, msg in (
        (f"ratelimit:ip:{ip}", 3600, PER_IP_HOURLY, f"Rate limit reached: {PER_IP_HOURLY} agent runs per hour. Try again later."),
        ("ratelimit:global", 86400, GLOBAL_DAILY, "The demo's daily AI budget is used up. Please come back tomorrow."),
    ):
        n = r.incr(key)
        if n == 1:
            r.expire(key, ttl)
        if n > cap:
            return msg
    return None


def _refuse(msg: str) -> StreamingResponse:
    async def job(emit):
        emit({"agent": "system", "kind": "error", "text": msg})
    return _sse(job)  # an SSE error event, so the UI shows the message instead of "stream disconnected"


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
    try:
        return [r[0] for r in tools._rows(_tenant(tenant), "MATCH (s:Service) RETURN s.id ORDER BY s.id")]
    except HTTPException:
        raise
    except Exception:  # database unreachable: serve the bundled synthetic data
        return sorted(s[0] for s in seed.SERVICES)


@app.get("/api/graph/{service_id}")
def graph(service_id: str, response: Response, tenant: str = "acme"):
    try:
        return tools.subgraph(_tenant(tenant), service_id)
    except HTTPException:
        raise
    except Exception:
        response.headers["X-Data-Source"] = "demo"  # the UI shows a "demo data" badge
        return demo.subgraph(service_id)


@app.get("/healthz")
def healthz():
    return {"ok": True}


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
    try:
        return tools.list_conversations(_tenant(tenant))
    except (DBConnectionError, DBTimeoutError):
        return []  # no history without a database; the chat view still opens


@app.get("/api/conversations/{cid}")
def conversation(cid: str, tenant: str = "acme"):
    try:
        return tools.chat_history(_tenant(tenant), cid, limit=200)
    except (DBConnectionError, DBTimeoutError):
        return []


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
async def chat(request: Request, message: str, conversation: str, mode: str = "ask", tenant: str = "acme"):
    """Server-sent events: one JSON event per agent step. mode=ask -> company-brain chat, mode=incident -> agents."""
    if not 0 < len(message) <= 4000 or not 0 < len(conversation) <= 64 or mode not in ("ask", "incident"):
        raise HTTPException(400, "bad request")
    tenant = _tenant(tenant)
    if msg := _over_limit(request):
        return _refuse(msg)
    if mode == "ask":
        return _sse(lambda emit: run_chat(message, conversation, tenant, emit))
    return _sse(lambda emit: _incident_turn(message, conversation, tenant, emit))


@app.get("/api/incident")
async def incident(request: Request, alert: str, tenant: str = "acme"):
    if not 0 < len(alert) <= 4000:
        raise HTTPException(400, "bad request")
    tenant = _tenant(tenant)
    if msg := _over_limit(request):
        return _refuse(msg)
    return _sse(lambda emit: run_incident(alert, tenant, emit=emit))


def _sse(job) -> StreamingResponse:
    q: asyncio.Queue = asyncio.Queue()

    async def worker():
        try:
            await job(q.put_nowait)
        except Exception as e:
            while hasattr(e, "exceptions") and e.exceptions:  # Unwrap TaskGroup / ExceptionGroup
                e = e.exceptions[0]
            text = "Graph database unreachable. Set FALKORDB_URL." if isinstance(e, (DBConnectionError, DBTimeoutError)) else str(e)
            q.put_nowait({"agent": "system", "kind": "error", "text": text})
        q.put_nowait(None)

    async def stream():
        task = asyncio.create_task(worker())
        try:
            while (ev := await q.get()) is not None:
                yield f"data: {json.dumps(ev, default=str)}\n\n"
        finally:
            task.cancel()  # client went away

    return StreamingResponse(stream(), media_type="text/event-stream")


app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")
