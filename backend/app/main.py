"""
FastAPI Backend Core - Executive Data Intelligence Suite
Provides multi-tenant endpoints for file analysis and Cohere AI execution.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import numpy as np
import os
import cohere

app = FastAPI(
    title="Executive Data Intelligence Suite - Backend",
    version="3.0.0"
)

# Enable CORS for local and cloud frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """Health check endpoint to confirm backend availability."""
    return {"status": "online", "service": "Executive BI FastAPI Backend"}

@app.post("/api/analyze")
async def analyze_dataset(file: UploadFile = File(...)):
    """
    Receives an uploaded CSV or Excel file, parses it, computes health scores, 
    field metrics, and returns a structured JSON payload for the frontend analytics grid.
    """
    try:
        contents = await file.read()
        filename = file.filename

        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        elif filename.endswith((".xls", ".xlsx")):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a .csv or .xlsx file.")

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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai-advisory")
async def generate_ai_advisory(payload: dict):
    """
    Receives verified summary stats from the frontend, communicates securely with Cohere server-side,
    and returns the structured executive business advisory.
    """
    api_key = os.getenv("COHERE_API_KEY")
    
    if not api_key:
        raise HTTPException(status_code=500, detail="COHERE_API_KEY is not configured on the backend environment.")
    
    try:
        co = cohere.Client(api_key)
        verified_stats = payload.get("verified_stats", "")
        
        prompt = f"""
        You are an expert Chief Business Financial Adviser. 
        Based ONLY on the verified dataset statistics provided below, provide a professional analysis structured into three clear sections:
        1. **Verified Findings**: State the core statistical facts derived from the data.
        2. **AI Interpretations**: Explain what these metrics mean for business performance.
        3. **Actionable Recommendations**: Give 3 concrete, practical steps the business owner should take next.
        
        {verified_stats}
        """
        
        response = co.chat(
            model="command-a-03-2025",
            message=prompt,
            temperature=0.3
        )
        return {"advisory": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))