"""
FastAPI Backend Core - Executive Data Intelligence Suite (Phase 0 Patched)
Powered by FastAPI, Pandas, and Cohere AI
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import io
import numpy as np
import os
import logging
import cohere

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="Executive Data Intelligence Suite - Secure Backend",
    version="6.2.0"
)

ALLOWED_ORIGINS = [
    "http://localhost:8501",
    "http://127.0.0.1:8501",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB strict upload cap

class AIAdvisoryRequest(BaseModel):
    verified_stats: str = Field(..., max_length=5000)

@app.get("/health")
def health_check(x_api_key: str = Header(None)):
    expected_token = os.getenv("BACKEND_SECRET_KEY")
    if not expected_token or x_api_key != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"status": "online", "service": "Secure BI FastAPI Backend"}

@app.post("/api/analyze")
async def analyze_dataset(file: UploadFile = File(...), x_api_key: str = Header(None)):
    expected_token = os.getenv("BACKEND_SECRET_KEY")
    if not expected_token or x_api_key != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="File too large (Max 10MB).")

        filename = file.filename
        try:
            df = pd.read_csv(io.BytesIO(contents), encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(contents), encoding="latin-1")
        except Exception:
            df = pd.read_excel(io.BytesIO(contents))

        total_records = len(df)
        fields_count = len(df.columns)
        total_cells = df.size
        missing_cells = df.isna().sum().sum()
        health_index = f"{max(0.0, min(100.0, ((total_cells - missing_cells) / max(1, total_cells)) * 100)):.1f}%"

        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()

        return {
            "filename": filename,
            "records": total_records,
            "fields_count": fields_count,
            "data_health_index": health_index,
            "numeric_columns": num_cols,
            "categorical_columns": cat_cols,
            "status": "success"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Internal analyze error: {str(e)}")
        raise HTTPException(status_code=500, detail="An internal processing error occurred.")

@app.post("/api/ai-advisory")
async def generate_ai_advisory(payload: AIAdvisoryRequest, x_api_key: str = Header(None)):
    expected_token = os.getenv("BACKEND_SECRET_KEY")
    if not expected_token or x_api_key != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="COHERE_API_KEY configuration missing.")
    
    try:
        co = cohere.Client(api_key)
        response = co.chat(
            model="command-a-03-2025",
            message=f"You are an expert Chief Business Financial Adviser. Based ONLY on the verified dataset statistics below, provide a professional executive analysis in 3 clear sections:\n\n{payload.verified_stats}",
            temperature=0.3
        )
        return {"advisory": response.text}
    except Exception as e:
        logger.error(f"Cohere AI error: {str(e)}")
        raise HTTPException(status_code=500, detail="AI advisory generation failed.")