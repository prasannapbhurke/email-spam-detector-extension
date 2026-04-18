from fastapi import FastAPI, HTTPException, Security, Request, Depends, Response
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import asyncio
import os
import time
import hashlib

from database import get_db, Feedback
from cache_service import cache_service
from model_utils import classifier
from phishing_detector import phishing_expert
from transformer_service import transformer_service
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Email Assistant")

# --- Security ---
API_KEY = os.getenv("API_KEY", "dev-secret-key-12345")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY: return api_key
    raise HTTPException(status_code=403, detail="Invalid API Key")

# --- PROPER CORS FIX ---
# Note: allow_credentials MUST be False when allow_origins is ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False, 
)

# Robust Manual Preflight Handler
@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request):
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

class PredictionRequest(BaseModel):
    email_text: str
    html_content: str = ""

@app.get("/")
async def root():
    return {"status": "online", "message": "Secure Bridge Active"}

@app.post("/predict")
async def predict(req: PredictionRequest, db: Session = Depends(get_db), api_key: str = Security(get_api_key)):
    try:
        # Cache Check
        cached = cache_service.get(req.email_text)
        if cached: return cached

        # Ensemble Logic
        ensemble_prob = await asyncio.to_thread(classifier.get_raw_spam_probability, req.email_text)
        phish_res = phishing_expert.scan(req.email_text, req.html_content)
        
        # Transformer Logic (Waking up cloud model)
        transformer_prob = await asyncio.to_thread(transformer_service.predict, req.email_text)
        
        confidence = (0.6 * transformer_prob) + (0.4 * ensemble_prob)
        if phish_res.get("isPhishing"):
            confidence = max(confidence, phish_res.get("phishingScore", 0))
        
        risk_score = int(confidence * 100)
        label = "Safe" if risk_score <= 30 else ("Suspicious" if risk_score <= 70 else "Dangerous")

        result = {
            "label": label,
            "risk_score": risk_score,
            "confidence": round(float(confidence), 4),
            "reasons": phish_res.get("reasons", []),
            "keywords": [k["word"] for k in classifier.get_explainability_weights(req.email_text)] if classifier.model else []
        }

        cache_service.set(req.email_text, result)
        return result
    except Exception as e:
        print(f"Server Error: {e}")
        return {"label": "Analyzed", "risk_score": 50, "confidence": 0.5, "reasons": ["AI system is optimizing..."], "keywords": []}

@app.post("/feedback")
async def feedback(data: Dict[str, Any], db: Session = Depends(get_db), api_key: str = Security(get_api_key)):
    try:
        new_feedback = Feedback(
            email_text=data.get("text"),
            prediction=data.get("prediction"),
            user_label=data.get("isActuallySpam")
        )
        db.add(new_feedback)
        db.commit()
        return {"status": "saved"}
    except:
        return {"status": "error"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
