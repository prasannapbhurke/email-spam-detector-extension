import re
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.svm import SVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import joblib
import os
from typing import List, Dict, Any

MODEL_PATH = "spam_model.joblib"

class SpamClassifier:
    def __init__(self):
        self.model = None

    def train(self, texts: List[str], labels: List[int]):
        lr = LogisticRegression(class_weight='balanced', max_iter=1000)
        rf = RandomForestClassifier(n_estimators=100, class_weight='balanced')
        svc = SVC(probability=True, kernel='linear', class_weight='balanced')
        nb = MultinomialNB()

        ensemble = VotingClassifier(
            estimators=[('lr', lr), ('rf', rf), ('svc', svc), ('nb', nb)],
            voting='soft'
        )

        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 3), max_features=5000)),
            ('ensemble', ensemble)
        ])
        
        self.model.fit(texts, labels)
        self.save()

    def save(self):
        joblib.dump(self.model, MODEL_PATH)

    def load(self):
        if os.path.exists(MODEL_PATH):
            self.model = joblib.load(MODEL_PATH)
            return True
        return False

    def get_raw_spam_probability(self, text: str) -> float:
        if not self.model:
            if not self.load(): return 0.5
        return float(self.model.predict_proba([text])[0][1])

    def get_explainability_weights(self, text: str):
        if not self.model: return []
        tfidf = self.model.named_steps['tfidf']
        lr = self.model.named_steps['ensemble'].named_estimators_['lr']
        feature_names = tfidf.get_feature_names_out()
        weights = lr.coef_[0]
        response = tfidf.transform([text])
        feature_index = response.nonzero()[1]
        contributions = []
        for index in feature_index:
            word = feature_names[index]
            importance = response[0, index] * weights[index]
            if importance > 0:
                contributions.append({"word": word, "importance": round(float(importance), 4)})
        contributions.sort(key=lambda x: x['importance'], reverse=True)
        return contributions[:5]

    def predict_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        if not self.model:
            if not self.load(): return []
        probs = self.model.predict_proba(texts)[:, 1]
        results = []
        for i, text in enumerate(texts):
            prob = float(probs[i])
            is_spam = prob > 0.5
            keywords = self.get_explainability_weights(text)
            results.append({
                "isSpam": bool(is_spam),
                "confidence": prob,
                "keywords": keywords
            })
        return results

classifier = SpamClassifier()
