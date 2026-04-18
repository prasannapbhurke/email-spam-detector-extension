from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, Any
import asyncio
import os

from fastapi import FastAPI, HTTPException, Security, Request, Depends, Response
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

from cache_service import cache_service
from database import get_db, Feedback, PredictionLog
from domain_analyzer import domain_analyzer
from model_utils import classifier
from phishing_detector import phishing_expert
from stylometry_analyzer import stylometry_analyzer
from transformer_service import transformer_service

load_dotenv()

app = FastAPI(title="AI Email Assistant")


class ForceCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)

        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS, DELETE, PUT"
        response.headers["Access-Control-Allow-Headers"] = "X-API-Key, Content-Type, Authorization"
        return response


app.add_middleware(ForceCORSMiddleware)

API_KEY = os.getenv("API_KEY", "dev-secret-key-12345")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)


async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return api_key
    raise HTTPException(status_code=403, detail="Invalid API Key")


class PredictionRequest(BaseModel):
    email_text: str
    html_content: str = ""
    analysis_mode: str = "full"


@app.on_event("startup")
async def startup_event():
    await asyncio.to_thread(classifier.load)


def determine_attack_type(phishing_score: float, domain_score: float, stylometry_score: float, hybrid_model_score: float) -> str:
    score_map = {
        "phishing": phishing_score,
        "domain": domain_score,
        "stylometry": stylometry_score,
        "spam": hybrid_model_score,
    }
    attack_type, value = max(score_map.items(), key=lambda item: item[1])
    return attack_type if value >= 0.2 else "benign"


def build_label(risk_score: int) -> str:
    if risk_score <= 30:
        return "Safe"
    if risk_score <= 70:
        return "Suspicious"
    return "Dangerous"


def build_reasons(phishing_result: Dict[str, Any], domain_result: Dict[str, Any], stylometry_result: Dict[str, Any]) -> list[str]:
    reasons = []
    reasons.extend(phishing_result.get("reasons", []))
    reasons.extend(domain_result.get("reasons", []))
    reasons.extend(stylometry_result.get("reasons", []))

    seen = set()
    deduped = []
    for reason in reasons:
        if reason not in seen:
            deduped.append(reason)
            seen.add(reason)
    return deduped


def build_keywords(text: str) -> list[str]:
    if not classifier.model:
        return []
    return [item["word"] for item in classifier.get_explainability_weights(text)]


def serialize_prediction(
    label: str,
    final_score: float,
    reasons: list[str],
    keywords: list[str],
    analysis_mode: str,
    hybrid_model_score: float,
    phishing_result: Dict[str, Any],
    domain_result: Dict[str, Any],
    stylometry_result: Dict[str, Any],
    attack_type: str,
    cached: bool = False,
) -> Dict[str, Any]:
    risk_score = int(round(final_score * 100))
    return {
        "label": label,
        "risk_score": risk_score,
        "confidence": round(final_score, 4),
        "reasons": reasons,
        "keywords": keywords,
        "analysis_mode": analysis_mode,
        "component_scores": {
            "hybrid_model": round(hybrid_model_score, 4),
            "phishing_score": round(phishing_result.get("phishingScore", 0.0), 4),
            "domain_score": round(domain_result.get("domain_score", 0.0), 4),
            "stylometry_score": round(stylometry_result.get("ai_generated_probability", 0.0), 4),
        },
        "domain_intelligence": {
            "domain_age_days": domain_result.get("domain_age_days"),
            "is_suspicious_tld": domain_result.get("is_suspicious_tld", False),
            "entropy_score": domain_result.get("entropy_score", 0.0),
            "is_blacklisted": domain_result.get("is_blacklisted", False),
            "primary_domain": domain_result.get("primary_domain"),
        },
        "stylometry": {
            "ai_generated_probability": stylometry_result.get("ai_generated_probability", 0.0),
            "type_token_ratio": stylometry_result.get("type_token_ratio", 0.0),
            "sentence_length_variance": stylometry_result.get("sentence_length_variance", 0.0),
        },
        "attack_type": attack_type,
        "cached": cached,
    }


def log_prediction(
    db: Session,
    email_text: str,
    result: Dict[str, Any],
    component_scores: Dict[str, float],
    attack_type: str,
    analysis_mode: str,
    cached: bool,
):
    log_entry = PredictionLog(
        email_text=email_text,
        label=result["label"],
        risk_score=result["risk_score"],
        hybrid_model_score=component_scores["hybrid_model"],
        phishing_score=component_scores["phishing_score"],
        domain_score=component_scores["domain_score"],
        stylometry_score=component_scores["stylometry_score"],
        attack_type=attack_type,
        cached=cached,
        analysis_mode=analysis_mode,
    )
    db.add(log_entry)
    db.commit()


@app.get("/")
async def root():
    return {"status": "online", "message": "AI Email Assistant"}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "modelLoaded": classifier.model is not None or classifier.load(),
        "transformerLoaded": getattr(transformer_service, "_initialized", False)
    }


@app.post("/predict")
async def predict(req: PredictionRequest, db: Session = Depends(get_db), api_key: str = Security(get_api_key)):
    try:
        analysis_mode = req.analysis_mode if req.analysis_mode in {"preview", "full"} else "full"
        cache_key = f"{analysis_mode}:{req.email_text}"
        cached = cache_service.get(cache_key)
        if cached:
            component_scores = cached.get("component_scores", {})
            log_prediction(
                db,
                req.email_text,
                cached,
                {
                    "hybrid_model": float(component_scores.get("hybrid_model", 0.0)),
                    "phishing_score": float(component_scores.get("phishing_score", 0.0)),
                    "domain_score": float(component_scores.get("domain_score", 0.0)),
                    "stylometry_score": float(component_scores.get("stylometry_score", 0.0)),
                },
                cached.get("attack_type", "benign"),
                analysis_mode,
                cached=True,
            )
            return {**cached, "cached": True}

        ensemble_prob = await asyncio.to_thread(classifier.get_raw_spam_probability, req.email_text)
        transformer_prob = 0.5
        if analysis_mode == "full" and len(req.email_text) > 80:
            transformer_prob = await asyncio.to_thread(transformer_service.predict, req.email_text)

        hybrid_model_score = ensemble_prob if analysis_mode == "preview" else ((0.6 * transformer_prob) + (0.4 * ensemble_prob))
        phishing_result = phishing_expert.scan(req.email_text, req.html_content)
        domain_result = domain_analyzer.analyze(req.email_text, req.html_content)
        stylometry_result = stylometry_analyzer.analyze(req.email_text)

        final_score = (
            0.5 * hybrid_model_score +
            0.2 * phishing_result.get("phishingScore", 0.0) +
            0.15 * domain_result.get("domain_score", 0.0) +
            0.15 * stylometry_result.get("ai_generated_probability", 0.0)
        )
        final_score = min(max(final_score, 0.0), 0.99)

        risk_score = int(round(final_score * 100))
        label = build_label(risk_score)
        reasons = build_reasons(phishing_result, domain_result, stylometry_result)
        keywords = build_keywords(req.email_text)
        attack_type = determine_attack_type(
            phishing_result.get("phishingScore", 0.0),
            domain_result.get("domain_score", 0.0),
            stylometry_result.get("ai_generated_probability", 0.0),
            hybrid_model_score,
        )

        result = serialize_prediction(
            label=label,
            final_score=final_score,
            reasons=reasons,
            keywords=keywords,
            analysis_mode=analysis_mode,
            hybrid_model_score=hybrid_model_score,
            phishing_result=phishing_result,
            domain_result=domain_result,
            stylometry_result=stylometry_result,
            attack_type=attack_type,
        )

        cache_service.set(cache_key, result)
        log_prediction(
            db,
            req.email_text,
            result,
            {
                "hybrid_model": hybrid_model_score,
                "phishing_score": phishing_result.get("phishingScore", 0.0),
                "domain_score": domain_result.get("domain_score", 0.0),
                "stylometry_score": stylometry_result.get("ai_generated_probability", 0.0),
            },
            attack_type,
            analysis_mode,
            cached=False,
        )
        return result
    except Exception as error:
        return {
            "label": "Analyzed",
            "risk_score": 50,
            "confidence": 0.5,
            "reasons": ["Processing fallback triggered."],
            "keywords": [],
            "error": str(error),
        }


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
    except Exception:
        return {"status": "error"}


@app.get("/stats")
async def stats(db: Session = Depends(get_db), api_key: str = Security(get_api_key)):
    total_scanned = db.query(func.count(PredictionLog.id)).scalar() or 0
    spam_detected = db.query(func.count(PredictionLog.id)).filter(PredictionLog.label.in_(["Suspicious", "Dangerous"])).scalar() or 0
    phishing_detected = db.query(func.count(PredictionLog.id)).filter(PredictionLog.attack_type == "phishing").scalar() or 0
    high_risk_count = db.query(func.count(PredictionLog.id)).filter(PredictionLog.risk_score >= 75).scalar() or 0

    return {
        "total_scanned": total_scanned,
        "spam_detected": spam_detected,
        "phishing_detected": phishing_detected,
        "high_risk_count": high_risk_count,
    }


@app.get("/weekly-report")
async def weekly_report(db: Session = Depends(get_db), api_key: str = Security(get_api_key)):
    since = datetime.utcnow() - timedelta(days=7)
    rows = db.query(PredictionLog).filter(PredictionLog.timestamp >= since).all()

    threats_avoided = sum(1 for row in rows if row.risk_score >= 45)
    attack_counter = Counter(row.attack_type for row in rows if row.attack_type and row.attack_type != "benign")
    most_common_attack_type = attack_counter.most_common(1)[0][0] if attack_counter else "benign"

    return {
        "threats_avoided": threats_avoided,
        "most_common_attack_type": most_common_attack_type,
        "sample_window_days": 7,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8002))
    uvicorn.run(app, host="0.0.0.0", port=port)
