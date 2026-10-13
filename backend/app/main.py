"""
FastAPI Backend (main.py) - Executive Intelligence Suite
Secured with API key enforcement, per-user rate limits, aggregate-only sanitization, and structured error responses.
"""

import hmac
import json
import logging
import os
import time
from collections import defaultdict, deque
from typing import Optional

import cohere
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

APP_VERSION = "1.2"
app = FastAPI(title="Executive Intelligence Backend", version=APP_VERSION)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

COHERE_MODEL = os.getenv("COHERE_MODEL", "command-r-plus-08-2024")
MAX_BODY_CHARS = 200_000


class AIAdvisoryRequest(BaseModel):
    verified_stats: dict
    saved_scenarios: Optional[list] = None


def require_key(x_api_key: str = Header(None)):
    expected = os.getenv("BACKEND_SECRET_KEY", "secure-default-key-2026")
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing API key.")


# ------------------------------------------------------------ rate limits
_user_hits = defaultdict(deque)
_global_hits = deque()


def _prune(q: deque, window: float):
    now = time.time()
    while q and now - q[0] > window:
        q.popleft()


def check_rate_limit(user: str):
    per_hour = int(os.getenv("AI_RATE_PER_HOUR", "10"))
    daily_cap = int(os.getenv("AI_DAILY_CAP", "500"))
    uq = _user_hits[user]
    _prune(uq, 3600)
    _prune(_global_hits, 86400)
    if len(uq) >= per_hour:
        raise HTTPException(status_code=429, detail=f"Rate limit reached ({per_hour} reports per hour). Try again later.")
    if len(_global_hits) >= daily_cap:
        raise HTTPException(status_code=429, detail="Daily service capacity reached. Try again tomorrow.")
    now = time.time()
    uq.append(now)
    _global_hits.append(now)


# ----------------------------------------------------------- sanitization
def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def sanitize_stats(stats: dict) -> dict:
    meta = stats.get("metadata") or {}
    return {
        "metadata": {k: meta.get(k) for k in (
            "total_records", "data_health_index", "missing_cells", "duplicate_rows", "anomaly_count",
            "revenue_column", "cost_column", "category_column", "date_column")},
        "totals": stats.get("totals"),
        "revenue_by_category": dict(list((stats.get("revenue_by_category") or {}).items())[:15]),
        "leaderboards": stats.get("leaderboards"),
        "concentration": stats.get("concentration"),
        "trend": stats.get("trend"),
        "anomaly_summary": stats.get("anomaly_summary"),
        "warnings": [str(w)[:300] for w in (stats.get("warnings") or [])[:10]],
    }


def sanitize_scenarios(scenarios: Optional[list]) -> list:
    out = []
    for sc in (scenarios or [])[:10]:
        if isinstance(sc, dict):
            out.append({
                "scenario_name": str(sc.get("scenario_name", ""))[:80],
                "revenue": _num(sc.get("revenue")), "costs": _num(sc.get("costs")),
                "net_profit": _num(sc.get("net_profit")), "margin": _num(sc.get("margin")),
            })
    return out


def build_prompt(stats: dict, scenarios: list) -> str:
    return f"""You are a friendly, practical business advisor writing for a small business owner with no finance background.
Write in plain, simple English with short sentences. Avoid jargon.
Analyze ONLY the data inside the <data> tags. Do NOT invent numbers.

<data>
VERIFIED DATASET FACT SHEET:
{json.dumps(stats, indent=1, default=str)}

SAVED WHAT-IF SCENARIOS:
{json.dumps(scenarios, indent=1) if scenarios else "None provided."}
</data>

Write the report in exactly these 6 markdown sections:
1. HOW THE BUSINESS IS DOING (money in, money spent, profit, margin)
2. WHAT SELLS BEST AND WHAT DOESN'T (top and weakest products or categories)
3. IS YOUR RECORD-KEEPING RELIABLE? (missing data, duplicates, unusually large sales)
4. THINGS TO WATCH OUT FOR (thin profit, relying on one product, other risks)
5. TRENDS AND YOUR WHAT-IF PLANS (how sales change over time and what the saved plans mean)
6. WHAT TO DO IN THE NEXT 30 / 60 / 90 DAYS (simple, practical steps tied to the numbers)
"""


def _call_cohere(api_key: str, prompt: str) -> str:
    co = cohere.ClientV2(api_key)
    resp = co.chat(model=COHERE_MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.2)
    return resp.message.content[0].text


# ----------------------------------------------------------------- routes
@app.get("/health", dependencies=[Depends(require_key)])
async def health_check():
    return {"status": "healthy", "service": "Executive Intelligence Backend", "version": APP_VERSION}


@app.post("/api/ai-advisory", dependencies=[Depends(require_key)])
async def generate_ai_advisory(payload: AIAdvisoryRequest, x_user_id: str = Header("anonymous")):
    if len(json.dumps(payload.model_dump(), default=str)) > MAX_BODY_CHARS:
        raise HTTPException(status_code=413, detail="Payload too large.")

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI service configuration missing.")

    check_rate_limit(x_user_id[:64])
    prompt = build_prompt(sanitize_stats(payload.verified_stats), sanitize_scenarios(payload.saved_scenarios))
    try:
        text = await run_in_threadpool(_call_cohere, api_key, prompt)
        return {"advisory": text}
    except Exception as e:
        logger.error("Cohere AI error: %s", e)
        raise HTTPException(status_code=502, detail="The AI provider request failed. Please try again.")