"""
FastAPI Backend (backend/app/main.py)
Updated with the active Cohere model ID (command-r-plus-08-2024) and 6-section structured advisory.
"""

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Any
import os
import cohere
import logging

app = FastAPI(title="Executive Intelligence Backend", version="6.11")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

class AIAdvisoryRequest(BaseModel):
    verified_stats: Any  # Accepts both dict and string payloads seamlessly

@app.get("/health")
async def health_check(x_api_key: str = Header(None)):
    expected_token = os.getenv("BACKEND_SECRET_KEY")
    if expected_token and x_api_key != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"status": "healthy", "service": "Executive Intelligence Backend"}

@app.post("/api/ai-advisory")
async def generate_ai_advisory(payload: AIAdvisoryRequest, x_api_key: str = Header(None)):
    expected_token = os.getenv("BACKEND_SECRET_KEY")
    if expected_token and x_api_key != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="COHERE_API_KEY configuration missing in environment variables.")
    
    try:
        co = cohere.Client(api_key)
        
        stats_content = payload.verified_stats if isinstance(payload.verified_stats, str) else str(payload.verified_stats)

        # 6-Section Structured Prompt with Strict Grounding
        prompt = f"""
        You are an elite Chief Financial Officer and Board Advisor. 
        Analyze the following verified dataset statistics strictly. DO NOT invent, assume, or extrapolate numbers not present in this dataset fact sheet. Every financial figure quoted must match the verified statistics verbatim.

        VERIFIED DATASET FACT SHEET:
        {stats_content}

        Provide a comprehensive, professional advisory report formatted strictly into the following 6 clear markdown sections:
        1. 📊 EXECUTIVE FINANCIAL HEALTH & SNAPSHOT (Evaluate revenue scale, cost absorption, net profit, and overall margin performance).
        2. 📦 PRODUCT & CATEGORY PERFORMANCE DEEP-DIVE (Analyze revenue shares, top contributors, and leaderboards).
        3. 🔍 DATA QUALITY AUDIT & ANOMALIES (Evaluate data health index, missing cells, duplicates, and outlier transactions).
        4. ⚠️ KEY STRATEGIC RISKS & VULNERABILITIES (Highlight margin pressures, concentration risks, and financial exposures).
        5. 📈 TRENDS & SCENARIO INSIGHTS (Interpret temporal patterns and sensitivity dynamics).
        6. 🚀 30 / 60 / 90-DAY ACTIONABLE RECOMMENDATIONS (Provide concrete, prioritized operational steps).
        """

        response = co.chat(
            model="command-r-plus-08-2024",  # Valid, active Cohere production model ID
            message=prompt,
            temperature=0.2  # Low temperature to prevent hallucinations
        )
        return {"advisory": response.text}
    except Exception as e:
        logger.error(f"Cohere AI error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cohere AI Error: {str(e)}")