# Smart Gmail Spam Detector

[![Tests](https://github.com/prasannapbhurke/email-spam-detector-extension/actions/workflows/tests.yml/badge.svg)](https://github.com/prasannapbhurke/email-spam-detector-extension/actions)
[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)

> AI-powered intelligent spam detection extension for Gmail with explainable AI results.

A production-style email spam detection system with Chrome extension integration, featuring multi-layer detection combining ML ensemble, transformer-based AI text detection, phishing scanning, domain analysis, and stylometry.

## Features

- **Multi-layer Detection**: Combines ML ensemble, transformer-based AI detection, phishing scanning, domain analysis, and stylometry
- **Explainable AI**: Shows keywords and reasons for each prediction
- **Real-time Scanning**: Automatically analyzes emails in Gmail
- **Quarantine Management**: Review and manage flagged emails through extension popup
- **Feedback Loop**: Submit corrections to improve the model
- **Statistics Dashboard**: Track spam detection performance over time
- **Caching**: Intelligent caching for faster repeated analysis

## Tech Stack

- **Backend**: Python 3.9+, FastAPI, scikit-learn, SQLite/PostgreSQL
- **ML Models**: TF-IDF + Ensemble (LogisticRegression, RandomForest, SVM, NaiveBayes)
- **Extension**: Chrome Extension (Manifest V3), JavaScript

## Architecture

```
email-spam-detector-extension/
├── backend/                          # FastAPI server
│   ├── main.py                       # API endpoints & orchestration
│   ├── database.py                   # SQLAlchemy models (Feedback, PredictionLog)
│   ├── model_utils.py                # ML ensemble classifier
│   ├── phishing_detector.py          # Phishing indicator scanner
│   ├── domain_analyzer.py           # Domain age/reputation analysis
│   ├── stylometry_analyzer.py      # AI-generated text detection
│   ├── transformer_service.py      # Transformer-based detection
│   ├── cache_service.py            # In-memory caching
│   ├── train_model.py            # Model training script
│   ├── retrain_pipeline.py       # Self-learning pipeline
│   └── requirements.txt
└── extension/                       # Chrome Extension
    ├── manifest.json               # Extension configuration
    ├── popup.html               # Extension popup UI
    ├── popup.js                # Popup logic
    ├── content.js              # Gmail content injection
    ├── api.js                # Backend API communication
    ├── ui.js                 # UI components
    ├── observer.js           # DOM observation
    └── styles.css            # Styling
```

## Quick Start

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
python main.py
```

The API runs on `http://localhost:8002`

### Chrome Extension Installation

1. Open `chrome://extensions`
2. Enable **Developer Mode** (top-right toggle)
3. Click **Load Unpacked**
4. Select the `extension` folder

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /` | GET | Health check |
| `GET /health` | GET | Detailed health status |
| `POST /predict` | POST | Analyze email text |
| `POST /feedback` | POST | Submit correction |
| `GET /stats` | GET | Detection statistics |
| `GET /weekly-report` | GET | Weekly threat report |

### Predict API

```bash
curl -X POST http://localhost:8002/predict \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret-key-12345" \
  -d '{"email_text": "Your email content here", "analysis_mode": "full"}'
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

## Detection Components

### 1. ML Ensemble Classifier
- LogisticRegression with TF-IDF (ngram_range: 1-3, max_features: 5000)
- RandomForest (100 estimators)
- SVM with linear kernel
- Multinomial NaiveBayes
- Voting ensemble for final prediction

### 2. Transformer-based AI Detection
- Detects AI-generated content patterns
- Analyzes writing style consistency
- Sentence structure analysis

### 3. Phishing Scanner
- Urgent/threatening language detection
- Suspicious link analysis
- Attachment indicators
- Impersonal patterns

### 4. Domain Analyzer
- Domain age verification
- TLD reputation scoring
- Entropy analysis for domain randomization
- Blacklist checking

### 5. Stylometry Analyzer
- Type-token ratio analysis
- Sentence length variance
- Writing pattern fingerprinting

## Scoring Algorithm

```
final_score = 0.5 * hybrid_model_score
           + 0.2 * phishing_score
           + 0.15 * domain_score
           + 0.15 * stylometry_score
```

| Risk Score | Label |
|------------|-------|
| 0-30 | Safe |
| 31-70 | Suspicious |
| 71-100 | Dangerous |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server port | `8002` |
| `API_KEY` | API authentication key | `dev-secret-key-12345` |
| `DATABASE_URL` | Database connection URI | SQLite local file |
| `TFIDF_MAX_FEATURES` | Max TF-IDF features | `5000` |

## Database Schema

### Feedback Table
- `id`: Primary key
- `email_text`: Original email content
- `prediction`: Original prediction
- `user_label`: Corrected label (spam/ham)
- `timestamp`: Submission time

### PredictionLog Table
- `id`: Primary key
- `email_text`: Email content
- `label`: Prediction label
- `risk_score`: Risk score (0-100)
- `component_scores`: Individual scores
- `attack_type`: Detected attack type
- `cached`: Cache hit flag
- `timestamp`: Analysis time

## Gmail Integration

The Chrome extension automatically:

1. **Monitors Gmail**: Uses MutationObserver to detect new emails
2. **Extracts Content**: Parses email subject and body
3. **Sends for Analysis**: Calls backend API with email content
4. **Displays Results**:Shows inline risk indicators
5. **Provides Actions**: Option to mark as spam/not spam

### Extension Permissions

- `storage`: Local data persistence
- `https://mail.google.com/*`: Gmail access
- `http://localhost:8002/*`: Local API access
- `https://*.up.railway.app/*`: Remote API access

## Self-Learning System

### Feedback Collection
Users can submit corrections via the extension popup or API:

```bash
curl -X POST http://localhost:8002/feedback \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret-key-12345" \
  -d '{"text": "original email", "prediction": "spam", "isActuallySpam": true}'
```

### Retraining Pipeline
Feedback data can be used to retrain and improve the model:

```bash
python retrain_pipeline.py --min-feedback 50
```

## Statistics Dashboard

### Endpoint: `/stats`

```json
{
  "total_scanned": 15420,
  "spam_detected": 3245,
  "phishing_detected": 892,
  "high_risk_count": 1234
}
```

### Endpoint: `/weekly-report`

```json
{
  "threats_avoided": 892,
  "most_common_attack_type": "phishing",
  "sample_window_days": 7
}
```

## Expected Performance

| Metric | Value |
|--------|-------|
| Accuracy | ~95% |
| Precision | ~94% |
| Recall | ~96% |
| F1-Score | ~95% |

*Performance may vary based on training data quality and volume.*

## Advanced AI Features

### LIME Explainability
Understanding why the model classified an email as spam:
- Feature importance visualization
- Word-level contribution analysis
- Human-readable explanations

### Phishing URL Detection
- Shortened URL detection (bit.ly, tinyurl, etc.)
- IP address URL detection
- Typosquatting recognition
- Suspicious TLD analysis

### Multi-Language Support
- English, Spanish, French, German
- Chinese, Japanese, Korean
- Language-specific spam patterns

## Deployment

### Railway (Recommended)

1. Connect GitHub repository
2. Set environment variables:
   - `DATABASE_URL`: PostgreSQL connection
   - `API_KEY`: Your secure API key
3. Deploy automatically

### Local Development

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run server
python backend/main.py
```

### Docker

```bash
docker build -t spam-detector .
docker run -p 8002:8002 -e DATABASE_URL=postgresql://... spam-detector
```

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read the [contributing guidelines](CONTRIBUTING.md) first.

## Security

See [SECURITY.md](SECURITY.md) for security vulnerability reporting.