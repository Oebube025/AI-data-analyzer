"""
FastAPI Backend (backend/app/main.py)
Executive Intelligence Suite - Phase 4 (Scenario-Aware AI Advisory & Robust Error Handling)
"""

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any
import os
import cohere
import logging

app = FastAPI(title="Executive Intelligence Backend", version="6.13")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

class AIAdvisoryRequest(BaseModel):
    verified_stats: Any
    saved_scenarios: Any = None  # Receives saved What-If simulation models from frontend

@app.get("/health")
async def health_check(x_api_key: str = Header(None)):
    expected_token = os.getenv("BACKEND_SECRET_KEY")
    if expected_token and x_api_key != expected_token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return {"status": "healthy", "service": "Executive Intelligence Backend"}

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
        
        # Format payload data cleanly into string representations for the prompt
        stats_content = payload.verified_stats if isinstance(payload.verified_stats, str) else str(payload.verified_stats)
        scenarios_content = f"\nSAVED WHAT-IF SCENARIOS:\n{payload.saved_scenarios}" if payload.saved_scenarios else "\nSAVED WHAT-IF SCENARIOS:\nNone provided."

        # 6-Section Structured Prompt with Strict Grounding & Scenario Awareness
        prompt = f"""
        You are an elite Chief Financial Officer and Board Advisor. 
        Analyze the following verified dataset statistics and any saved simulation scenarios strictly. DO NOT invent, assume, or extrapolate numbers not present in this data. Every financial figure quoted must match the verified statistics verbatim.

        VERIFIED DATASET FACT SHEET:
        {stats_content}
        {scenarios_content}

        Provide a comprehensive, professional advisory report formatted strictly into the following 6 clear markdown sections:
        1. 📊 EXECUTIVE FINANCIAL HEALTH & SNAPSHOT (Evaluate revenue scale, cost absorption, net profit, and overall margin performance).
        2. 📦 PRODUCT & CATEGORY PERFORMANCE DEEP-DIVE (Analyze revenue shares, top contributors, and leaderboards).
        3. 🔍 DATA QUALITY AUDIT & ANOMALIES (Evaluate data health index, missing cells, duplicates, and outlier transactions).
        4. ⚠️ KEY STRATEGIC RISKS & VULNERABILITIES (Highlight margin pressures, concentration risks, and financial exposures).
        5. 📈 TRENDS & SCENARIO INSIGHTS (Interpret temporal patterns and explicitly evaluate the strategic implications of any saved What-If scenarios).
        6. 🚀 30 / 60 / 90-DAY ACTIONABLE RECOMMENDATIONS (Provide concrete, prioritized operational steps reflecting baseline metrics and simulated targets).
        """

        response = co.chat(
            model="command-r-plus-08-2024",  # Active Cohere production model
            message=prompt,
            temperature=0.2                  # Low temperature to prevent hallucinations
        )
        return {"advisory": response.text}
    except Exception as e:
        logger.error(f"Cohere AI error: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": f"Cohere AI Error: {str(e)}"})