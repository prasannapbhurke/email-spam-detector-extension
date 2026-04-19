# Smart Gmail Spam Detector

AI-powered spam detection extension for Gmail with explainable AI results.

## Features

- **Multi-layer Detection**: Combines ML ensemble, transformer-based AI detection, phishing scanning, domain analysis, and stylometry
- **Explainable AI**: Shows keywords and reasons for each prediction
- **Real-time Scanning**: Automatically analyzes emails in Gmail
- **Quarantine Management**: Review and manage flagged emails
- **Feedback Loop**: Submit corrections to improve the model
- **Statistics Dashboard**: Track spam detection performance

## Tech Stack

- **Backend**: Python FastAPI, scikit-learn ensemble, SQLite/PostgreSQL
- **Extension**: Chrome Extension (Manifest V3)

## Architecture

```
email-spam-detector-extension/
├── backend/           # FastAPI server
│   ├── main.py       # API endpoints
│   ├── model_utils.py
│   ├── phishing_detector.py
│   ├── domain_analyzer.py
│   └── stylometry_analyzer.py
└── extension/       # Chrome Extension
    ├── manifest.json
    ├── popup.html
    └── content.js
```

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

The API runs on `http://localhost:8002`

### Chrome Extension

1. Open `chrome://extensions`
2. Enable Developer Mode
3. Click "Load Unpacked"
4. Select the `extension` folder

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/predict` | POST | Analyze email text |
| `/feedback` | POST | Submit correction |
| `/stats` | GET | Detection statistics |
| `/weekly-report` | GET | Weekly threat report |

## Detection Components

1. **ML Ensemble**: LogisticRegression + RandomForest + SVM + NaiveBayes
2. **Transformer**: AI-generated text detection
3. **Phishing Scanner**: Urgent language, links, attachments
4. **Domain Analyzer**: Domain age, TLD reputation, blacklists
5. **Stylometry**: Writing pattern analysis