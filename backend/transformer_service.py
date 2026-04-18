import os

try:
    import torch
    import torch.nn.functional as F
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
except ImportError:
    torch = None
    F = None
    AutoTokenizer = None
    AutoModelForSequenceClassification = None


class TransformerService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TransformerService, cls).__new__(cls)
            cls._instance.tokenizer = None
            cls._instance.model = None
            cls._instance.device = None
            cls._instance._initialized = False
            cls._instance._load_attempted = False
        return cls._instance

    def _lazy_load(self):
        if self._initialized:
            return

        if self._load_attempted:
            return

        self._load_attempted = True

        if AutoTokenizer is None or AutoModelForSequenceClassification is None or torch is None or F is None:
            print("Transformer dependencies not installed. Falling back to classic ML only.")
            return

        model_name = os.getenv("TRANSFORMER_MODEL", "distilbert-base-uncased")

        try:
            print("Loading transformer model...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                num_labels=2,
                local_files_only=True
            )
            self.device = torch.device("cpu")
            self.model.to(self.device)
            self.model.eval()
            self._initialized = True
            print("Transformer ready.")
        except Exception as error:
            print(f"Transformer load failed: {error}")
            self.tokenizer = None
            self.model = None

    def predict(self, text: str) -> float:
        self._lazy_load()

        if not self.model or not self.tokenizer or torch is None or F is None:
            return 0.5

        try:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = F.softmax(outputs.logits, dim=-1)
                return probs[0][1].item()
        except Exception as error:
            print(f"Inference error: {error}")
            return 0.5


transformer_service = TransformerService()
