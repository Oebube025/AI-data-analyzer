"""
FastAPI Backend Core - Executive Data Intelligence Suite (Roadmap V6)
Powered by DuckDB, Cohere AI, and FastAPI
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import duckdb
import io
import numpy as np
import os
import cohere

app = FastAPI(
    title="Executive Data Intelligence Suite - Advanced Backend",
    version="6.0.0"
)

ALLOWED_ORIGINS = [
    "http://localhost:8501",
    "http://127.0.0.1:8501",
    "https://your-streamlit-app-domain.streamlit.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB strict upload cap
duck_conn = duckdb.connect(database=":memory:")

class AIAdvisoryRequest(BaseModel):
    verified_stats: str = Field(..., max_length=5000)

class QueryRequest(BaseModel):
    sql_query: str = Field(..., max_length=1000)

class SimulationRequest(BaseModel):
    price_factor: float
    volume_factor: float
    revenue_col: str
    cost_col: str

@app.get("/health")
def health_check(x_api_key: str = Header(None)):
    expected_token = os.getenv("BACKEND_SECRET_KEY")
    if not expected_token or x_api_key != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"status": "online", "service": "Advanced BI FastAPI Backend"}

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
        df = pd.read_csv(io.BytesIO(contents), encoding="utf-8") if filename.lower().endswith(".csv") else pd.read_excel(io.BytesIO(contents))
        
        # Register dataset in DuckDB in-memory engine
        duck_conn.register("dataset", df)

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

@app.post("/api/query")
def execute_sql_query(req: QueryRequest, x_api_key: str = Header(None)):
    expected_token = os.getenv("BACKEND_SECRET_KEY")
    if not expected_token or x_api_key != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        result_df = duck_conn.execute(req.sql_query).fetchdf()
        return result_df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/simulate")
def run_simulation(req: SimulationRequest, x_api_key: str = Header(None)):
    expected_token = os.getenv("BACKEND_SECRET_KEY")
    if not expected_token or x_api_key != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        query = f"""
            SELECT 
                SUM("{req.revenue_col}") * {req.price_factor} * {req.volume_factor} AS simulated_revenue,
                SUM("{req.cost_col}") * {req.volume_factor} AS simulated_cost
            FROM dataset
        """ if req.cost_col != "None" else f"""
            SELECT 
                SUM("{req.revenue_col}") * {req.price_factor} * {req.volume_factor} AS simulated_revenue,
                0.0 AS simulated_cost
            FROM dataset
        """
        res_df = duck_conn.execute(query).fetchdf()
        rev = float(res_df['simulated_revenue'].iloc[0])
        cost = float(res_df['simulated_cost'].iloc[0])
        return {"simulated_revenue": rev, "simulated_cost": cost, "simulated_profit": rev - cost}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/ai-advisory")
async def generate_ai_advisory(payload: AIAdvisoryRequest, x_api_key: str = Header(None)):
    expected_token = os.getenv("BACKEND_SECRET_KEY")
    if not expected_token or x_api_key != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="COHERE_API_KEY missing.")
    
    try:
        co = cohere.Client(api_key)
        response = co.chat(
            model="command-a-03-2025",
            message=f"You are an expert Chief Business Financial Adviser. Based ONLY on the verified dataset statistics below, provide a professional analysis in 3 sections:\n\n{payload.verified_stats}",
            temperature=0.3
        )
        return {"advisory": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))