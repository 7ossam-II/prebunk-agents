"""Async OpenAI-compatible chat client with on-disk cache, retries and a mock backend."""
import asyncio
import hashlib
import json
import os
import random
import re
import sqlite3
import time

import httpx


class FatalAPIError(Exception):
    """Errors that retrying cannot fix (bad key, no balance, unknown model)."""


class Cache:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS c (k TEXT PRIMARY KEY, v TEXT)")
        self.db.commit()

    def get(self, k):
        r = self.db.execute("SELECT v FROM c WHERE k=?", (k,)).fetchone()
        return json.loads(r[0]) if r else None

    def put(self, k, v):
        self.db.execute("INSERT OR REPLACE INTO c VALUES (?,?)", (k, json.dumps(v)))
        self.db.commit()


class LLM:
    def __init__(self, backend="mock", model="deepseek-flash", base_url="https://api.deepseek.com",
                 api_key=None, temperature=0.7, concurrency=16, cache_path="results/cache.sqlite",
                 timeout=60, max_retries=6):
        self.backend = backend
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        self.temperature = temperature
        self.sem = asyncio.Semaphore(concurrency)
        self.cache = Cache(cache_path)
        self.timeout = timeout
        self.max_retries = max_retries
        self.usage = {"calls": 0, "cached": 0, "prompt_tokens": 0, "completion_tokens": 0, "failures": 0}
        self.client = None
        self.fatal = False
        if backend == "openai" and not self.api_key:
            raise FatalAPIError("No API key. Set LLM_API_KEY (or DEEPSEEK_API_KEY) in your environment.")

    async def __aenter__(self):
        if self.backend == "openai":
            self.client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, *a):
        if self.client:
            await self.client.aclose()

    def _key(self, system, user, tag):
        raw = json.dumps([self.backend, self.model, self.temperature, system, user, tag])
        return hashlib.sha256(raw.encode()).hexdigest()

    async def chat(self, system, user, tag=""):
        """Return the assistant text. `tag` separates replicate samples of the same prompt."""
        k = self._key(system, user, tag)
        hit = self.cache.get(k)
        if hit is not None:
            self.usage["cached"] += 1
            return hit
        async with self.sem:
            if self.backend == "mock":
                self.usage["calls"] += 1
                text = _mock_reply(system, user, tag)
            else:
                text = await self._call(system, user)
        if text is not None:
            self.cache.put(k, text)
        return text

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def check(self):
        """Fail fast with a readable message: is the key valid and does the model exist?"""
        if self.backend != "openai":
            return
        try:
            r = await self.client.get(f"{self.base_url}/models", headers=self._headers())
        except httpx.HTTPError as e:
            raise FatalAPIError(f"Cannot reach {self.base_url}: {e}")
        if r.status_code == 401:
            raise FatalAPIError("The API key was rejected (401). Check that LLM_API_KEY is set to a valid key.")
        if r.status_code == 200:
            ids = [m.get("id") for m in r.json().get("data", [])]
            if ids and self.model not in ids:
                raise FatalAPIError(f"Model '{self.model}' is not available. Use --model with one of: {', '.join(ids)}")
            print(f"API OK. Model: {self.model}", flush=True)

    async def _call(self, system, user):
        if self.fatal:
            return None
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
            "max_tokens": 2000,
        }
        if "deepseek.com" in self.base_url:
            # DeepSeek V4 models think by default; the simulation needs fast non-thinking replies,
            # and temperature only works in non-thinking mode.
            payload["thinking"] = {"type": "disabled"}
        delay = 2.0
        for attempt in range(self.max_retries):
            try:
                r = await self.client.post(f"{self.base_url}/chat/completions", json=payload, headers=self._headers())
                if r.status_code == 200:
                    d = r.json()
                    u = d.get("usage", {})
                    self.usage["calls"] += 1
                    if self.usage["calls"] % 250 == 0:
                        print(f"  ... {self.usage['calls']} API calls done", flush=True)
                    self.usage["prompt_tokens"] += u.get("prompt_tokens", 0)
                    self.usage["completion_tokens"] += u.get("completion_tokens", 0)
                    return d["choices"][0]["message"]["content"]
                if r.status_code in (400, 401, 402, 403, 404):
                    if not self.fatal:
                        self.fatal = True
                        hint = " Top up your account balance." if r.status_code == 402 else ""
                        raise FatalAPIError(f"API error {r.status_code}: {r.text[:300]}{hint}")
                    return None
            except (httpx.TimeoutException, httpx.TransportError):
                pass
            await asyncio.sleep(delay + random.random())
            delay = min(delay * 2, 60)
        self.usage["failures"] += 1
        return None


# ---------------------------------------------------------------------------
# Mock backend: cheap, deterministic stand-in used only to test the pipeline.
# Its numbers mean nothing scientifically.
# ---------------------------------------------------------------------------
_CONSPIRACY = re.compile(r"Government|Manipulat|Controlled|Toxins|Caused by|Lie to|New Study|Extremism", re.I)


def _mock_reply(system, user, tag):
    rng = random.Random(hashlib.md5((system + user + tag).encode()).hexdigest())
    inoc = "Heads up" in system
    low_trust = "trust in mainstream news media is low" in system
    if "categorize each" in user:
        answers = {}
        for line in user.splitlines():
            m = re.match(r"(\d+)\. (.*)", line)
            if m:
                fakeish = bool(_CONSPIRACY.search(m.group(2)))
                p_fake = (0.75 if fakeish else 0.25) + (0.12 if inoc and fakeish else 0) - (0.1 if low_trust and fakeish else 0)
                answers[m.group(1)] = "Fake" if rng.random() < p_fake else "Real"
        return json.dumps({"answers": answers})
    headline = user.split('"')[1] if '"' in user else ""
    m = re.search(r"(\d+) of your friends", user)
    k = int(m.group(1)) if m else 1
    fakeish = bool(_CONSPIRACY.search(headline))
    base = 4.5 if not fakeish else 3.2 + (0.8 if low_trust else 0)
    believe = max(1, min(7, round(base + 0.25 * min(k, 4) - (1.3 if inoc and fakeish else 0) + rng.gauss(0, 1))))
    share = rng.random() < (0.08 + 0.07 * believe - (0.08 if inoc and fakeish else 0))
    return json.dumps({"believe": believe, "share": share, "reason": "mock"})
