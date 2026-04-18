import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch.nn.functional as F

class TransformerService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TransformerService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.model_name = "distilbert-base-uncased"
        try:
            # Note: In production, ideally load a fine-tuned version
            # Using base model here for architectural implementation
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name, num_labels=2)
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            self.model.eval()
            self._initialized = True
            print(f"Transformer model {self.model_name} loaded successfully on {self.device}")
        except Exception as e:
            print(f"Error loading transformer model: {e}")
            self.model = None

    def predict(self, text: str) -> float:
        """Returns spam probability (0-1)"""
        if not self.model:
            return 0.5 # Neutral fallback
        
        try:
            inputs = self.tokenizer(
                text, 
                return_tensors="pt", 
                truncation=True, 
                max_length=512
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = F.softmax(outputs.logits, dim=-1)
                # Label 1 is typically spam in binary datasets
                spam_prob = probs[0][1].item()
                return spam_prob
        except Exception as e:
            print(f"Transformer inference error: {e}")
            return 0.5

transformer_service = TransformerService()
