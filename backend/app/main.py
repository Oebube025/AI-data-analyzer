"""
FastAPI Backend Core - Executive Data Intelligence Suite
Provides multi-tenant endpoints for file analysis and Cohere AI execution.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import io
import os
import cohere

app = FastAPI(
    title="Executive Data Intelligence API",
    version="3.0.0",
    description="Enterprise Decoupled Backend Service"
)

# Enable CORS so your Streamlit client can talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str
    model: str = "command-a-03-2025"

@app.get("/")
def home():
    return {"status": "online", "message": "Executive Data Intelligence API is running!"}

@app.post("/api/v1/analyze-file")
async def analyze_file(file: UploadFile = File(...)):
    """Accepts uploaded dataset files and returns high-level health metrics."""
    contents = await file.read()
    ext = os.path.splitext(file.filename)[-1].lower()
    
    buffer = io.BytesIO(contents)
    if ext == ".csv":
        df = pd.read_csv(buffer)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(buffer)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format.")

    total_cells = df.shape[0] * df.shape[1]
    missing_cells = df.isnull().sum().sum()
    health_score = round(((total_cells - missing_cells) / total_cells) * 100, 1) if total_cells > 0 else 100

    return {
        "filename": file.filename,
        "records": df.shape[0],
        "fields_count": df.shape[1],
        "data_health_index": f"{health_score}%",
        "columns": list(df.columns)
    }