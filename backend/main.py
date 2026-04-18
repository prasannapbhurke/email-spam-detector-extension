from fastapi import FastAPI, HTTPException, Security, Request
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field, field_validator
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import asyncio
import bleach
import os
from model_utils import classifier
from phishing_detector import phishing_expert
from transformer_service import transformer_service
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Secure XAI Hybrid Spam API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"], 
    allow_headers=["*"],
)

API_KEY = os.getenv("API_KEY", "dev-secret-key-12345")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY: return api_key
    raise HTTPException(status_code=403, detail="Invalid API Key")

class PredictionRequest(BaseModel):
    email_text: str = Field(..., min_length=1)
    html_content: str = Field("")

class PredictionResponse(BaseModel):
    label: str
    risk_score: int
    confidence: float
    reasons: List[str]
    keywords: List[str]

@app.post("/predict", response_model=PredictionResponse)
async def predict(req: PredictionRequest, api_key: str = Security(get_api_key)):
    # 1. Standard Ensemble Prediction
    ml_results = await asyncio.to_thread(classifier.predict_batch, [req.email_text])
    ensemble_score = ml_results[0]["confidence"] if ml_results else 0.5
    ensemble_keywords = [k["word"] for k in ml_results[0]["contributingKeywords"]] if ml_results else []
    
    # 2. Transformer Prediction (DistilBERT)
    transformer_score = await asyncio.to_thread(transformer_service.predict, req.email_text)
    
    # 3. Phishing Expert Analysis
    phish_res = phishing_expert.scan(req.email_text, req.html_content)
    
    # 4. Hybrid Scoring Formula
    # final_score = 0.6 * transformer + 0.4 * ensemble
    final_confidence = (0.6 * transformer_score) + (0.4 * ensemble_score)
    
    # Boost if phishing detected manually
    if phish_res["isPhishing"]:
        final_confidence = max(final_confidence, phish_res["phishingScore"])
    
    # 5. Risk Score Conversion
    risk_score = int(final_confidence * 100)
    
    if risk_score <= 30:
        label = "Safe"
    elif risk_score <= 70:
        label = "Suspicious"
    else:
        label = "Dangerous"

    # 6. Aggregate Reasons
    reasons = phish_res["reasons"]
    if transformer_score > 0.8 and not phish_res["reasons"]:
        reasons.append("Neural patterns match known malicious communication styles")
    if not reasons and label != "Safe":
        reasons.append("High probability detected by structural analysis")

    return {
        "label": label,
        "risk_score": risk_score,
        "confidence": round(final_confidence, 4),
        "reasons": reasons,
        "keywords": ensemble_keywords
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
