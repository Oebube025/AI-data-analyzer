"""
FastAPI Backend (backend/app/main.py)
Friendly AI Fractional CFO Advisory Endpoint with Safe JSON Responses.
"""

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any
import os
import cohere
import logging

app = FastAPI(title="SME AI CFO Backend", version="7.1")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

class AIAdvisoryRequest(BaseModel):
    verified_stats: Any
    saved_scenarios: Any = None

@app.get("/health")
async def health_check(x_api_key: str = Header(None)):
    expected_token = os.getenv("BACKEND_SECRET_KEY")
    if expected_token and x_api_key != expected_token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return {"status": "healthy", "service": "SME AI CFO Backend"}

@app.post("/api/ai-advisory")
async def generate_ai_advisory(payload: AIAdvisoryRequest, x_api_key: str = Header(None)):
    expected_token = os.getenv("BACKEND_SECRET_KEY")
    if expected_token and x_api_key != expected_token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        return JSONResponse(
            status_code=500, 
            content={"detail": "COHERE_API_KEY configuration missing in environment variables."}
        )
    
    try:
        co = cohere.Client(api_key)
        stats_content = payload.verified_stats if isinstance(payload.verified_stats, str) else str(payload.verified_stats)
        scenarios_content = f"\nSAVED WHAT-IF SCENARIOS:\n{payload.saved_scenarios}" if payload.saved_scenarios else "\nSAVED WHAT-IF SCENARIOS:\nNone created yet."

        # Plain-English AI CFO Advisory Prompt for SMEs
        prompt = f"""
        You are an experienced, friendly Fractional CFO advising a small business owner. 
        Analyze the verified business data and simulation scenarios below strictly. DO NOT invent, assume, or fabricate any figures. Every financial number quoted must match the facts verbatim. Speak clearly without corporate jargon.

        VERIFIED BUSINESS DATA FACT SHEET:
        {stats_content}
        {scenarios_content}

        Provide a clear, plain-English advisory report formatted strictly into these 6 SME-focused sections:
        1. 💡 THE BOTTOM LINE (Evaluate total money in, operating costs, net profit, and take-home margin %).
        2. 🏆 BEST & WORST PERFORMERS (Highlight top-selling products/categories vs underperforming lines).
        3. 🚨 DATA RED FLAGS & CLEANUP (Highlight missing entries, duplicate rows, or unusual transactions).
        4. 💸 PROFIT LEAKAGE & RISKS (Point out thin profit margins, cost spikes, and revenue concentration risks).
        5. 🔮 WHAT-IF LOOKAHEAD (Explain what happens to net profit under saved pricing or volume scenarios).
        6. 🎯 THIS MONTH'S TOP 3 ACTION ITEMS (Provide 3 concrete, non-technical steps the owner should take right now).
        """

        response = co.chat(
            model="command-r-plus-08-2024",
            message=prompt,
            temperature=0.2  # Low temperature enforces strict grounding
        )
        return {"advisory": response.text}
    except Exception as e:
        logger.error(f"Cohere AI error: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": f"Cohere AI Error: {str(e)}"})