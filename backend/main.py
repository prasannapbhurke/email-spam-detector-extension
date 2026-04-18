from fastapi import FastAPI, HTTPException, Security, Request, Depends, BackgroundTasks
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import asyncio
import os
import time

from database import get_db, Feedback
from cache_service import cache_service
from model_utils import classifier
from phishing_detector import phishing_expert
from transformer_service import transformer_service
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Production-Grade AI Email Assistant")

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

# --- Preload Models at Startup ---
@app.on_event("startup")
async def startup_event():
    print("Preloading models...")
    classifier.load()
    # Accessing transformer_service triggers singleton initialization
    _ = transformer_service
    print("All models ready.")

# --- Models ---
class PredictionRequest(BaseModel):
    email_text: str
    html_content: str = ""

class QuarantineRequest(BaseModel):
    message_id: str
    sender_email: str

# --- Retraining Logic ---
def check_and_trigger_retraining(db: Session):
    count = db.query(Feedback).count()
    if count >= 100:
        print(f"Threshold reached ({count} samples). Triggering retraining pipeline...")
        # In production, this would trigger retrain_pipeline.py via subprocess or Celery
        os.system("python retrain_pipeline.py &")

# --- Routes ---
@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/predict")
async def predict(req: PredictionRequest, db: Session = Depends(get_db), api_key: str = Security(get_api_key)):
    # 1. Caching Layer
    cached = cache_service.get(req.email_text)
    if cached: return cached

    # 2. Hybrid Inference
    ensemble_prob = await asyncio.to_thread(classifier.get_raw_spam_probability, req.email_text)
    transformer_prob = await asyncio.to_thread(transformer_service.predict, req.email_text)
    
    # 3. Cybersecurity Expert
    phish_res = phishing_expert.scan(req.email_text, req.html_content)
    
    # 4. Hybrid Formula
    confidence = (0.6 * transformer_prob) + (0.4 * ensemble_prob)
    if phish_res["isPhishing"]:
        confidence = max(confidence, phish_res["phishingScore"])
    
    risk_score = int(confidence * 100)
    label = "Safe" if risk_score <= 30 else ("Suspicious" if risk_score <= 70 else "Dangerous")

    # 5. Build Explanation
    reasons = phish_res["reasons"]
    if transformer_prob > 0.8: reasons.append("Neural analysis matches scam patterns")
    
    result = {
        "label": label,
        "risk_score": risk_score,
        "confidence": round(confidence, 4),
        "reasons": reasons,
        "keywords": [k["word"] for k in classifier.get_explainability_weights(req.email_text)]
    }

    # 6. Store in Cache
    cache_service.set(req.email_text, result)
    return result

@app.post("/feedback")
async def feedback(data: Dict[str, Any], background_tasks: BackgroundTasks, db: Session = Depends(get_db), api_key: str = Security(get_api_key)):
    new_feedback = Feedback(
        email_text=data.get("text"),
        prediction=data.get("prediction"),
        user_label=data.get("isActuallySpam")
    )
    db.add(new_feedback)
    db.commit()
    
    background_tasks.add_task(check_and_trigger_retraining, db)
    return {"status": "saved"}

@app.post("/quarantine")
async def quarantine(req: QuarantineRequest, api_key: str = Security(get_api_key)):
    # Placeholder for Gmail API integration
    # Requirement: mark as spam + archive
    print(f"QUARANTINE: Archiving message {req.message_id} and blocking {req.sender_email}")
    return {"status": "success", "action": "archived_and_flagged"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
