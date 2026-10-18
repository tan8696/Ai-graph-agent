"""Checks the Gemini caps in app.py without FalkorDB or Gemini.  Run: python test_rate_limit.py"""
import os
from types import SimpleNamespace

os.environ["RATE_LIMIT_PER_IP_HOUR"] = "2"
os.environ["RATE_LIMIT_GLOBAL_DAY"] = "3"

from fastapi.testclient import TestClient

import app


class FakeRedis(dict):
    def incr(self, k):
        self[k] = self.get(k, 0) + 1
        return self[k]

    def expire(self, k, ttl):
        pass


app.tools._db = lambda: SimpleNamespace(connection=FakeRedis.instance)
FakeRedis.instance = FakeRedis()


async def fake_chat(message, cid, tenant, emit):
    emit({"agent": "system", "kind": "done", "answer": "ok"})


app.run_chat = fake_chat
client = TestClient(app.app)


def ask(ip):
    r = client.get("/api/chat", params={"message": "hi", "conversation": "c1"}, headers={"x-forwarded-for": ip})
    return r.text


assert '"done"' in ask("1.1.1.1")
assert '"done"' in ask("1.1.1.1")
assert "per hour" in ask("1.1.1.1")       # 3rd call from the same IP is refused
assert '"done"' in ask("2.2.2.2")         # another IP still works (global count now 3)
assert "daily AI budget" in ask("3.3.3.3")  # global cap reached
print("rate limit checks passed")
