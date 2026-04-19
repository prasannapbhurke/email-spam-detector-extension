# Smart Gmail Spam Detector

[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

> AI-powered intelligent spam detection extension for Gmail with Chrome extension integration.

This project provides a production-style email spam detection with Chrome browser extension.

## Tech Stack

- **Backend**: Python 3.9+, FastAPI, scikit-learn (ensemble), SQLAlchemy
- **ML Models**: TF-IDF + Ensemble (LogisticRegression, RandomForest, SVM, NaiveBayes)
- **Extension**: Chrome Extension (Manifest V3)

## Features

- Multi-layer spam detection system
- ML ensemble classifier with TF-IDF features
- Transformer-based AI text detection
- Phishing indicator scanner
- Domain age and reputation analyzer
- Stylometry analysis (AI-generated text detection)
- Chrome extension for Gmail
- Quarantine management
- Self-learning via feedback

## Architecture

```
email-spam-detector-extension/
├── backend/
│   ├── main.py                    # FastAPI server
│   ├── database.py               # Database models
│   ├── model_utils.py           # ML ensemble classifier
│   ├── phishing_detector.py    # Phishing scanner
│   ├── domain_analyzer.py     # Domain analysis
│   ├── stylometry_analyzer.py # AI text detection
│   ├── transformer_service.py # Transformer service
│   └── cache_service.py      # Caching
└── extension/
    ├── manifest.json
    ├── popup.html
    ├── content.js
    ├── api.js
    ├── ui.js
    └── observer.js
```

## Backend Setup

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Server runs on `http://localhost:8002`

### Prediction API

```bash
curl -X POST http://localhost:8002/predict \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret-key-12345" \
  -d '{"email_text": "Your email content", "analysis_mode": "full"}'
```

Response:
```json
{
  "label": "Dangerous",
  "risk_score": 85,
  "confidence": 0.85,
  "reasons": ["Contains urgent language", "Suspicious links detected"],
  "keywords": ["free", "winner", "claim"],
  "attack_type": "phishing",
  "component_scores": {
    "hybrid_model": 0.82,
    "phishing_score": 0.91,
    "domain_score": 0.45,
    "stylometry_score": 0.23
  }
}
```

## Chrome Extension Setup

1. Open `chrome://extensions`
2. Enable **Developer Mode**
3. Click **Load Unpacked**
4. Select the `extension` folder

---

## Quick Test

```bash
# Start the API server
python backend/main.py

# Test a prediction
python -c "
from model_utils import classifier
classifier.load()
prob = classifier.get_raw_spam_probability('WIN FREE MONEY NOW!!!')
print(f'Spam probability: {prob:.2%}')
"
```

---

## Detection Components

### 1. ML Ensemble Classifier
- TF-IDF (ngram_range: 1-3, max_features: 5000)
- LogisticRegression, RandomForest, SVM, NaiveBayes
- Voting ensemble

### 2. Transformer-based AI Detection
- AI-generated text patterns
- Writing style analysis

### 3. Phishing Scanner
- Urgent language detection
- Suspicious links
- Attachment indicators

### 4. Domain Analyzer
- Domain age verification
- TLD reputation scoring
- Blacklist checking
- Entropy analysis

### 5. Stylometry Analyzer
- Type-token ratio
- Sentence length variance
- Writing pattern fingerprinting

### Scoring Algorithm

```
final_score = 0.5 * hybrid_model
          + 0.2 * phishing_score
          + 0.15 * domain_score
          + 0.15 * stylometry_score
```

| Risk Score | Label |
|------------|-------|
| 0-30 | Safe |
| 31-70 | Suspicious |
| 71-100 | Dangerous |

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /` | GET | Health check |
| `GET /health` | GET | Detailed health |
| `POST /predict` | POST | Analyze email |
| `POST /feedback` | POST | Submit correction |
| `GET /stats` | GET | Statistics |
| `GET /weekly-report` | GET | Weekly report |

### Feedback API

```bash
curl -X POST http://localhost:8002/feedback \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret-key-12345" \
  -d '{"text": "original email", "prediction": "spam", "isActuallySpam": true}'
```

### Statistics

```bash
curl -X GET http://localhost:8002/stats \
  -H "X-API-Key: dev-secret-key-12345"
```

Response:
```json
{
  "total_scanned": 15420,
  "spam_detected": 3245,
  "phishing_detected": 892,
  "high_risk_count": 1234
}
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `8002` |
| `API_KEY` | API key | `dev-secret-key-12345` |
| `DATABASE_URL` | Database URL | SQLite file |

---

## Training

```bash
python train_model.py --data path/to/dataset.csv
```

Dataset format:
- `text`: Email content
- `label`: `spam`/`ham` or `1`/`0`

---

## Deployment

### Railway

1. Connect GitHub repository
2. Set environment variables
3. Deploy

### Docker

```bash
docker build -t spam-detector .
docker run -p 8002:8002 spam-detector
```

---

## License

MIT License - See [LICENSE](LICENSE) for details.