import math
import re
from typing import Dict, Any, List


FORMAL_PHRASES = {
    "dear user",
    "kindly note",
    "please be advised",
    "we would like to inform you",
    "your prompt attention",
    "at your earliest convenience",
}


class StylometryAnalyzer:
    def _sentences(self, text: str) -> List[str]:
        sentences = re.split(r'(?<=[.!?])\s+|\n+', text.strip())
        return [sentence.strip() for sentence in sentences if sentence.strip()]

    def _tokens(self, text: str) -> List[str]:
        return re.findall(r"[a-zA-Z']+", text.lower())

    def _type_token_ratio(self, tokens: List[str]) -> float:
        if not tokens:
            return 1.0
        return len(set(tokens)) / len(tokens)

    def _sentence_length_variance(self, sentences: List[str]) -> float:
        if len(sentences) < 2:
            return 0.0
        lengths = [len(self._tokens(sentence)) for sentence in sentences]
        mean = sum(lengths) / len(lengths)
        variance = sum((length - mean) ** 2 for length in lengths) / len(lengths)
        normalized = variance / max(mean ** 2, 1)
        return round(min(normalized, 1.0), 3)

    def _formal_tone_score(self, text: str) -> float:
        lowered = text.lower()
        matches = sum(1 for phrase in FORMAL_PHRASES if phrase in lowered)
        exclamation_penalty = lowered.count("!") * 0.03
        return round(min(1.0, matches * 0.22 + exclamation_penalty), 3)

    def _repetition_score(self, sentences: List[str]) -> float:
        if len(sentences) < 2:
            return 0.0
        starts = [re.sub(r'[^a-z ]', '', sentence.lower()).split()[:3] for sentence in sentences]
        start_phrases = [" ".join(tokens) for tokens in starts if tokens]
        duplicates = len(start_phrases) - len(set(start_phrases))
        return round(min(1.0, duplicates / max(1, len(sentences) - 1)), 3)

    def analyze(self, text: str) -> Dict[str, Any]:
        sentences = self._sentences(text)
        tokens = self._tokens(text)
        type_token_ratio = round(self._type_token_ratio(tokens), 3)
        sentence_variance = self._sentence_length_variance(sentences)
        formal_tone_score = self._formal_tone_score(text)
        repetition_score = self._repetition_score(sentences)

        ai_probability = (
            (1 - min(type_token_ratio / 0.75, 1.0)) * 0.35 +
            (1 - min(sentence_variance / 0.18, 1.0)) * 0.25 +
            formal_tone_score * 0.2 +
            repetition_score * 0.2
        )

        reasons = []
        if type_token_ratio < 0.35:
            reasons.append("Low lexical diversity detected.")
        if sentence_variance < 0.08 and len(sentences) >= 3:
            reasons.append("Repetitive sentence structure detected.")
        if formal_tone_score > 0.3:
            reasons.append("Overly formal tone detected.")

        return {
            "ai_generated_probability": round(min(max(ai_probability, 0.0), 0.99), 2),
            "type_token_ratio": type_token_ratio,
            "sentence_length_variance": sentence_variance,
            "formal_tone_score": formal_tone_score,
            "repetition_score": repetition_score,
            "reasons": reasons
        }


stylometry_analyzer = StylometryAnalyzer()
