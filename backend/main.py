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
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY", "dev-secret-key-12345")
API_KEY_NAME = "X-API-Key"
FEEDBACK_FILE = "feedback_data.json"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY: return api_key
    raise HTTPException(status_code=403, detail="Could not validate credentials")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Self-Learning XAI Spam Detection API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"], 
    allow_headers=["*"],
)

prediction_cache: Dict[str, Dict[str, Any]] = {}

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
        return bleach.clean(v, tags=[], strip=True)

class FeedbackData(BaseModel):
    id: str
    text: str
    isActuallySpam: bool

@app.get("/")
async def root():
    return {"status": "ok", "service": "Self-Learning Spam API"}

@app.get("/export_feedback")
async def export_feedback(api_key: str = Security(get_api_key)):
    """Allows the developer to download collected feedback for local retraining."""
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "r") as f:
            return json.load(f)
    return []

@app.post("/predict")
@limiter.limit("60/minute")
async def predict(request: Request, email: EmailData, api_key: str = Security(get_api_key)):
    content = email.text or f"{email.subject} {email.snippet} {email.body}"
    content = content.strip()
    if not content: raise HTTPException(status_code=422, detail="No content provided")

    email_id = email.id.strip() or hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    if email_id in prediction_cache: return {"id": email_id, **prediction_cache[email_id]}

    result = await asyncio.to_thread(classifier.predict_batch, [content])
    if not result: raise HTTPException(status_code=503, detail="Model unavailable")
    
    prediction = result[0]
    prediction_cache[email_id] = prediction
    return {"id": email_id, **prediction}

@app.post("/feedback")
async def receive_feedback(feedback: FeedbackData, api_key: str = Security(get_api_key)):
    new_entry = {"text": feedback.text, "label": 1 if feedback.isActuallySpam else 0}
    data = []
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "r") as f:
            try: data = json.load(f)
            except: data = []
    data.append(new_entry)
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(data, f, indent=4)
    return {"status": "success", "total_feedback": len(data)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
