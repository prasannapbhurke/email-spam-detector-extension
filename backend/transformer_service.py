import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch.nn.functional as F
import os

class TransformerService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TransformerService, cls).__new__(cls)
            cls._instance.tokenizer = None
            cls._instance.model = None
            cls._instance._initialized = False
        return cls._instance

    def _lazy_load(self):
        """Loads the model only when needed to prevent startup hang."""
        if self._initialized:
            return
        
        print("📥 First-time use: Loading Transformer model (DistilBERT)...")
        model_name = "distilbert-base-uncased"
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)
            self.device = torch.device("cpu") # Force CPU for Railway stability
            self.model.to(self.device)
            self.model.eval()
            self._initialized = True
            print("✅ Transformer ready.")
        except Exception as e:
            print(f"❌ Failed to load transformer: {e}")

    def predict(self, text: str) -> float:
        self._lazy_load()
        if not self.model:
            return 0.5
        
        try:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = F.softmax(outputs.logits, dim=-1)
                return probs[0][1].item()
        except Exception as e:
            print(f"Inference error: {e}")
            return 0.5

transformer_service = TransformerService()
