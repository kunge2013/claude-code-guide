"""
NER Model Configuration.

Configuration for BERT-based Named Entity Recognition model.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class NERConfig:
    """Configuration for NER model training and inference."""

    # Model settings
    model_name: str = "hfl/chinese-bert-wwm-ext"
    max_seq_length: int = 128
    num_labels: int = 13  # O + 6 entity types * 2 (B/I)

    # Entity labels (BIO format)
    label_list: List[str] = field(default_factory=lambda: [
        "O",
        "B-PRODUCT", "I-PRODUCT",
        "B-TIME", "I-TIME",
        "B-FIELD", "I-FIELD",
        "B-ORG", "I-ORG",
        "B-PERSON", "I-PERSON",
        "B-LOCATION", "I-LOCATION",
    ])

    # Training settings
    num_train_epochs: int = 10
    learning_rate: float = 2e-5
    batch_size: int = 16
    warmup_steps: int = 500
    weight_decay: float = 0.01
    gradient_accumulation_steps: int = 1

    # Evaluation settings
    eval_steps: int = 500
    save_steps: int = 1000
    logging_steps: int = 100

    # Model paths
    output_dir: str = "models/ner_bert"
    cache_dir: Optional[str] = None

    # Inference settings
    device: str = "cuda"  # or "cpu"
    use_fp16: bool = False
    confidence_threshold: float = 0.8

    def __post_init__(self):
        """Validate configuration after initialization."""
        self.num_labels = len(self.label_list)
        if self.device == "cuda" and not self._is_cuda_available():
            self.device = "cpu"

    @staticmethod
    def _is_cuda_available() -> bool:
        """Check if CUDA is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def get_label2id(self) -> dict:
        """Get label to ID mapping."""
        return {label: i for i, label in enumerate(self.label_list)}

    def get_id2label(self) -> dict:
        """Get ID to label mapping."""
        return {i: label for i, label in enumerate(self.label_list)}
