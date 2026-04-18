from fastapi import FastAPI, HTTPException, Security, Request
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field, field_validator
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import asyncio
import bleach
import hashlib
import os
import json
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from model_utils import classifier
from phishing_detector import phishing_expert # New expert module
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY", "dev-secret-key-12345")
API_KEY_NAME = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY: return api_key
    raise HTTPException(status_code=403, detail="Could not validate credentials")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Cybersecurity-Enhanced XAI Spam API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"], 
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    classifier.load()

class EmailData(BaseModel):
    id: str = Field("")
    subject: str = Field("")
    sender: str = Field("")
    snippet: str = Field("")
    body: str = Field("")
    text: str = Field("")

    @field_validator("body", "subject", "snippet", "sender", "text")
    @classmethod
    def sanitize_content(cls, v):
        return bleach.clean(v, tags=['a'], attributes={'a': ['href']}, strip=True) # Keep links for phishing scan

class PhishingStatus(BaseModel):
    isPhishing: bool
    phishingScore: float
    reasons: List[str]

class PredictionResponse(BaseModel):
    id: str
    isSpam: bool
    confidence: float
    explanation: str
    technicalExplanation: Optional[str] = None
    contributingKeywords: Optional[List[Dict[str, Any]]] = None
    phishingAnalysis: PhishingStatus # Cybersecurity integration

@app.post("/predict", response_model=PredictionResponse)
@limiter.limit("60/minute")
async def predict(request: Request, email: EmailData, api_key: str = Security(get_api_key)):
    content = email.text or f"{email.subject} {email.snippet} {email.body}"
    raw_body = email.body # Use raw body to check for link mismatches
    
    if not content.strip(): raise HTTPException(status_code=422, detail="No content")

    # 1. Run Standard Spam ML
    ml_result = await asyncio.to_thread(classifier.predict_batch, [content])
    if not ml_result: raise HTTPException(status_code=503, detail="ML Model offline")
    res = ml_result[0]

    # 2. Run Cybersecurity Phishing Scan
    phish_res = phishing_expert.scan(content, raw_body)
    
    # 3. Hybrid Logic: If it's phishing, it's definitely spam
    final_is_spam = res["isSpam"] or phish_res["isPhishing"]
    final_confidence = max(res["confidence"], phish_res["phishingScore"])
    
    # Enrich explanation if phishing is detected
    explanation = res["explanation"]
    if phish_res["isPhishing"]:
        explanation = f"⚠️ PHISHING ALERT: {phish_res['reasons'][0]}. " + explanation

    return {
        "id": email.id or "unk",
        "isSpam": final_is_spam,
        "confidence": final_confidence,
        "explanation": explanation,
        "technicalExplanation": res["technicalExplanation"],
        "contributingKeywords": res["contributingKeywords"],
        "phishingAnalysis": phish_res
    }

@app.post("/feedback")
async def receive_feedback(feedback: Dict[str, Any], api_key: str = Security(get_api_key)):
    # Existing feedback logic...
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
