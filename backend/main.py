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
from phishing_detector import phishing_expert
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
app = FastAPI(title="AI Email Assistant API")
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

    @field_validator("body", "subject", "snippet", "sender")
    @classmethod
    def sanitize_content(cls, v):
        return bleach.clean(v, tags=['a'], attributes={'a': ['href']}, strip=True)

class FeedbackData(BaseModel):
    id: str
    text: str
    isActuallySpam: bool

class PredictionResponse(BaseModel):
    id: str
    isSpam: bool
    confidence: float
    intentSummary: str  # Product feature: Intent analysis
    warningMessage: Optional[str] = None # Product feature: Specific warnings
    suggestedFilter: str # Product feature: Automation
    contributingKeywords: List[Dict[str, Any]]
    technicalExplanation: Optional[str] = None

def generate_intent(is_spam: bool, phish_res: dict, keywords: list) -> str:
    if phish_res["isPhishing"]:
        return "Urgent: This sender is attempting to compromise your security by requesting sensitive information."
    if is_spam:
        top_words = [k['word'] for k in keywords[:2]] if keywords else ["suspicious patterns"]
        return f"Promotional: Likely an unsolicited attempt to sell services or products related to '{', '.join(top_words)}'."
    return "Authentic: This looks like a legitimate standard communication."

@app.get("/")
async def root():
    return {"status": "ok", "service": "AI Email Assistant"}

@app.post("/predict", response_model=PredictionResponse)
@limiter.limit("60/minute")
async def predict(request: Request, email: EmailData, api_key: str = Security(get_api_key)):
    content = f"{email.subject} {email.snippet} {email.body}"
    content = content.strip() or "Empty Content"

    email_id = email.id.strip() or hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    
    # Check cache
    if email_id in prediction_cache:
        return {"id": email_id, **prediction_cache[email_id]}

    # 1. Run ML Analysis
    ml_res = await asyncio.to_thread(classifier.predict_batch, [content])
    phish_res = phishing_expert.scan(content, email.body)
    
    res = ml_res[0]
    is_spam = res["isSpam"] or phish_res["isPhishing"]
    
    # 2. Generate Product Logic
    intent = generate_intent(is_spam, phish_res, res["contributingKeywords"])
    
    try:
        domain = email.sender.split('@')[-1].split('>')[0]
    except:
        domain = "sender"

    warning = phish_res["reasons"][0] if phish_res["reasons"] else None

    result = {
        "id": email_id,
        "isSpam": is_spam,
        "confidence": max(res["confidence"], phish_res["phishingScore"]),
        "intentSummary": intent,
        "warningMessage": warning,
        "suggestedFilter": f"from:{domain}",
        "contributingKeywords": res["contributingKeywords"],
        "technicalExplanation": res["technicalExplanation"]
    }
    
    prediction_cache[email_id] = result
    return result

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
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
