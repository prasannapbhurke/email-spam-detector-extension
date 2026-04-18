from fastapi import FastAPI, HTTPException, Security, Request, Depends, BackgroundTasks
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

app = FastAPI(title="Production AI Email Assistant")

# --- Security ---
API_KEY = os.getenv("API_KEY", "dev-secret-key-12345")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY: return api_key
    raise HTTPException(status_code=403, detail="Invalid API Key")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("🚀 Server starting up...")
    # Load ensemble model (fast)
    classifier.load()
    print("✅ Ensemble model loaded.")

# --- Models ---
class PredictionRequest(BaseModel):
    email_text: str
    html_content: str = ""

# --- Routes ---
@app.get("/")
async def root():
    return {"status": "online", "message": "AI Assistant Backend is Running"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "ensemble_loaded": classifier.model is not None,
        "transformer_init": transformer_service._initialized if hasattr(transformer_service, '_initialized') else False
    }

@app.post("/predict")
async def predict(req: PredictionRequest, db: Session = Depends(get_db), api_key: str = Security(get_api_key)):
    try:
        # 1. Caching Layer
        cached = cache_service.get(req.email_text)
        if cached: return cached

        # 2. Hybrid Inference with Fallback
        ensemble_prob = 0.5
        try:
            ensemble_prob = await asyncio.to_thread(classifier.get_raw_spam_probability, req.email_text)
        except Exception as e:
            print(f"Ensemble error: {e}")

        # Lazy load transformer to prevent timeout
        transformer_prob = 0.5
        try:
            transformer_prob = await asyncio.to_thread(transformer_service.predict, req.email_text)
        except Exception as e:
            print(f"Transformer error: {e}")
        
        # 3. Cybersecurity Expert
        phish_res = phishing_expert.scan(req.email_text, req.html_content)
        
        # 4. Hybrid Formula (Weighted)
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

        # 5. Store in Cache
        cache_service.set(req.email_text, result)
        return result
    except Exception as e:
        print(f"Prediction crash: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
