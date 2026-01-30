"""
T5 Model Configuration.

Configuration for T5-based question rewriting model.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class T5Config:
    """Configuration for T5 Seq2Seq model training and inference."""

    # Model settings
    model_name: str = "uer/t5-small"
    max_source_length: int = 128
    max_target_length: int = 128

    # Training settings
    num_train_epochs: int = 5
    learning_rate: float = 3e-4
    batch_size: int = 8
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01

    # Generation settings
    num_beams: int = 4
    no_repeat_ngram_size: int = 2
    early_stopping: bool = True
    length_penalty: float = 0.6
    max_length: int = 128

    # Evaluation settings
    eval_steps: int = 200
    save_steps: int = 500
    logging_steps: int = 50

    # Model paths
    output_dir: str = "models/rewrite_t5"
    cache_dir: Optional[str] = None

    # Inference settings
    device: str = "cuda"  # or "cpu"
    use_fp16: bool = False

    # Prefix for generation
    generation_prefix: str = "改写问题："

    def __post_init__(self):
        """Validate configuration after initialization."""
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
