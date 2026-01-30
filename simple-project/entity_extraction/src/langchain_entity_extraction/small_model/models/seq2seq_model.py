"""
T5-based Question Rewriting Model.

Implements a Seq2Seq model for question rewriting using T5.
"""

from typing import List, Dict, Any, Optional

import torch
from transformers import T5Tokenizer, T5ForConditionalGeneration, AutoTokenizer, AutoModelForSeq2SeqLM


class QuestionRewriteModel:
    """
    T5-based question rewriting model.

    Loads a pre-trained T5 model fine-tuned for question rewriting
    and provides methods for generating rewritten questions.

    Example:
        >>> from langchain_entity_extraction.small_model.config import T5Config
        >>> from langchain_entity_extraction.small_model.models import QuestionRewriteModel
        >>>
        >>> config = T5Config()
        >>> model = QuestionRewriteModel("models/rewrite_t5", config)
        >>> rewritten = model.rewrite("今年cdn产品金额是多少")
    """

    def __init__(
        self,
        model_path: str,
        config: Optional["T5Config"] = None,
        device: Optional[str] = None
    ):
        """
        Initialize the T5 model.

        Args:
            model_path: Path to the trained model (or HuggingFace model name)
            config: T5Config object (optional, will use defaults if not provided)
            device: Device to use ("cuda", "cpu", or None for auto)
        """
        from langchain_entity_extraction.small_model.config.t5_config import T5Config
        from langchain_entity_extraction.small_model.utils.model_utils import ModelUtils

        self.config = config or T5Config()
        self.device = ModelUtils.get_device(device)

        # Load tokenizer and model
        # Try T5-specific tokenizer first, fall back to AutoTokenizer
        try:
            self.tokenizer = T5Tokenizer.from_pretrained(
                model_path,
                cache_dir=self.config.cache_dir
            )
        except Exception:
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                cache_dir=self.config.cache_dir
            )

        self.model = T5ForConditionalGeneration.from_pretrained(
            model_path,
            cache_dir=self.config.cache_dir
        )

        # Move model to device
        self.model.to(self.device)
        self.model.eval()  # Set to evaluation mode

        # Set generation parameters from config
        self.generation_kwargs = {
            "max_length": self.config.max_length,
            "num_beams": self.config.num_beams,
            "no_repeat_ngram_size": self.config.no_repeat_ngram_size,
            "early_stopping": self.config.early_stopping,
            "length_penalty": self.config.length_penalty,
        }

    def rewrite(
        self,
        question: str,
        entities: Optional[Dict[str, Any]] = None,
        **generation_kwargs
    ) -> str:
        """
        Rewrite a single question.

        Args:
            question: Original question
            entities: Optional entity dict for context
            **generation_kwargs: Override generation parameters

        Returns:
            Rewritten question string

        Example:
            >>> model = QuestionRewriteModel("models/rewrite_t5")
            >>> model.rewrite("今年cdn产品金额是多少")
            "产品ID为cdn，时间为2026年的出账金额是多少"
        """
        with torch.no_grad():
            # Prepare input with prefix
            input_text = self._prepare_input(question, entities)

            # Tokenize
            inputs = self.tokenizer(
                input_text,
                return_tensors="pt",
                truncation=True,
                max_length=self.config.max_source_length,
                padding=True
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Merge generation kwargs
            gen_kwargs = {**self.generation_kwargs, **generation_kwargs}

            # Generate
            outputs = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                **gen_kwargs
            )

            # Decode
            rewritten = self.tokenizer.decode(
                outputs[0],
                skip_special_tokens=True
            )

        return rewritten.strip()

    def rewrite_batch(
        self,
        questions: List[str],
        entities_list: Optional[List[Dict[str, Any]]] = None,
        **generation_kwargs
    ) -> List[str]:
        """
        Rewrite multiple questions.

        Args:
            questions: List of original questions
            entities_list: Optional list of entity dicts (one per question)
            **generation_kwargs: Override generation parameters

        Returns:
            List of rewritten question strings
        """
        if entities_list is None:
            entities_list = [None] * len(questions)

        with torch.no_grad():
            # Prepare inputs
            input_texts = [
                self._prepare_input(q, e)
                for q, e in zip(questions, entities_list)
            ]

            # Tokenize batch
            inputs = self.tokenizer(
                input_texts,
                return_tensors="pt",
                truncation=True,
                max_length=self.config.max_source_length,
                padding=True
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Merge generation kwargs
            gen_kwargs = {**self.generation_kwargs, **generation_kwargs}

            # Generate
            outputs = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                **gen_kwargs
            )

            # Decode all
            rewritten = [
                self.tokenizer.decode(o, skip_special_tokens=True).strip()
                for o in outputs
            ]

        return rewritten

    def _prepare_input(
        self,
        question: str,
        entities: Optional[Dict[str, Any]]
    ) -> str:
        """
        Prepare input text with prefix.

        Args:
            question: Original question
            entities: Optional entity dict

        Returns:
            Formatted input text
        """
        # Add prefix
        prefix = self.config.generation_prefix

        # If entities provided, we could include them as context
        # For now, just use the question
        return f"{prefix}{question}"

    def get_confidence(self, question: str) -> float:
        """
        Get confidence score for the rewriting.

        This is a heuristic based on the model's output probabilities.
        Note: T5 doesn't naturally provide confidence scores for generation,
        so this returns a placeholder.

        Args:
            question: Input question

        Returns:
            Confidence score (placeholder, returns 0.85)
        """
        # For generation models, true confidence is hard to compute
        # This is a placeholder - could be implemented using
        # log probabilities or ensemble methods
        return 0.85

    def rewrite_with_beam_search(
        self,
        question: str,
        num_beams: int = 5,
        num_return_sequences: int = 1
    ) -> List[str]:
        """
        Rewrite with beam search, returning multiple candidates.

        Args:
            question: Original question
            num_beams: Number of beams for beam search
            num_return_sequences: Number of candidates to return

        Returns:
            List of candidate rewrites
        """
        with torch.no_grad():
            input_text = self._prepare_input(question, None)

            inputs = self.tokenizer(
                input_text,
                return_tensors="pt",
                truncation=True,
                max_length=self.config.max_source_length,
                padding=True
            )

            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            outputs = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_length=self.config.max_length,
                num_beams=num_beams,
                no_repeat_ngram_size=self.config.no_repeat_ngram_size,
                early_stopping=self.config.early_stopping,
                length_penalty=self.config.length_penalty,
                num_return_sequences=num_return_sequences,
                do_sample=False  # Use deterministic beam search
            )

            candidates = [
                self.tokenizer.decode(o, skip_special_tokens=True).strip()
                for o in outputs
            ]

        return candidates


class SimpleT5Rewriter(torch.nn.Module):
    """
    Simple T5 rewriter implementation for training.

    This is a minimal implementation that wraps the T5 model
    for training on custom rewriting data.
    """

    def __init__(
        self,
        model_name: str = "uer/t5-small",
        max_length: int = 128
    ):
        """
        Initialize the model.

        Args:
            model_name: Pre-trained T5 model name
            max_length: Maximum generation length
        """
        super().__init__()

        self.model = T5ForConditionalGeneration.from_pretrained(model_name)
        self.tokenizer = T5Tokenizer.from_pretrained(model_name)
        self.max_length = max_length

    def forward(self, input_ids, attention_mask, labels=None):
        """
        Forward pass.

        Args:
            input_ids: Input token IDs
            attention_mask: Attention mask
            labels: Optional labels for computing loss

        Returns:
            Dict with loss (if labels provided) and logits
        """
        outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels
        )

        return {
            "loss": outputs.loss,
            "logits": outputs.logits
        }

    def generate(self, input_ids, attention_mask, **kwargs):
        """Generate sequences."""
        return self.model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            **kwargs
        )
