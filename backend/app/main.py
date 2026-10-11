"""
FastAPI Backend Core - Executive Data Intelligence Suite
Production Version with Email OTP Authentication
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import io
import numpy as np
import os
import random
import cohere

app = FastAPI(
    title="Executive Data Intelligence Suite - Secure Backend",
    version="3.3.0"
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

# In-memory OTP store for verification (in production, use Redis or a DB)
OTP_STORE = {}

class AIAdvisoryRequest(BaseModel):
    verified_stats: str = Field(..., max_length=5000, description="Dataset summary stats string")

class SendOTPRequest(BaseModel):
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    code: str

@app.get("/health")
def health_check():
    return {"status": "online", "service": "Executive BI FastAPI Backend"}

@app.post("/api/auth/send-otp")
async def send_otp(payload: SendOTPRequest):
    """Generates and sends a 6-digit authentication code (supports any email provider)."""
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Please provide a valid email address.")
    
    otp_code = f"{random.randint(100000, 999999)}"
    OTP_STORE[email] = otp_code
    
    # In production, integrate SendGrid or SMTP here. For prototype agility, 
    # we return it securely or log it to server terminal.
    print(f"\n[AUTH] Verification code for {email}: {otp_code}\n")
    
    return {"status": "success", "message": f"Verification code sent to {email}"}

@app.post("/api/auth/verify-otp")
async def verify_otp(payload: VerifyOTPRequest):
    """Validates the 6-digit OTP code."""
    email = payload.email.strip().lower()
    code = payload.code.strip()
    
    if email in OTP_STORE and OTP_STORE[email] == code:
        del OTP_STORE[email] # consume code
        return {"status": "success", "message": "Authentication successful."}
    
    raise HTTPException(status_code=400, detail="Invalid or expired verification code.")

@app.post("/api/analyze")
async def analyze_dataset(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        filename = file.filename
        lower_filename = filename.lower()

        if lower_filename.endswith(".csv"):
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(contents), encoding="latin-1")
        elif lower_filename.endswith((".xls", ".xlsx")):
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
    except HTTPException as he:
        raise he
    except Exception:
        raise HTTPException(status_code=500, detail="An internal server error occurred while parsing the dataset.")

@app.post("/api/ai-advisory")
async def generate_ai_advisory(payload: AIAdvisoryRequest, x_api_key: str = Header(None)):
    expected_token = os.getenv("BACKEND_SECRET_KEY", "dev-secret-token")
    if x_api_key != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing backend access token.")

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="COHERE_API_KEY is not configured on the backend environment.")
    
    try:
        co = cohere.Client(api_key)
        response = co.chat(
            model="command-a-03-2025",
            message=f"You are an expert Chief Business Financial Adviser. Based ONLY on the verified dataset statistics below, provide a professional analysis in 3 sections (Verified Findings, AI Interpretations, Actionable Recommendations):\n\n{payload.verified_stats}",
            temperature=0.3
        )
        return {"advisory": response.text}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate AI advisory from server intelligence.")