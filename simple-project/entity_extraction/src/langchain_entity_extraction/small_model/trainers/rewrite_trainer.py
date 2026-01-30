"""
Rewrite Model Trainer.

Training script for T5-based question rewriting model.
"""

import os
from typing import List, Dict, Any, Optional

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    T5Tokenizer,
    T5ForConditionalGeneration,
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq
)

from langchain_entity_extraction.small_model.config.t5_config import T5Config
from langchain_entity_extraction.small_model.preprocessors.rewrite_preprocessor import RewritePreprocessor


class RewriteDataset(Dataset):
    """Dataset for question rewriting training."""

    def __init__(
        self,
        data: List[Dict],
        tokenizer: Any,
        max_source_length: int = 128,
        max_target_length: int = 128,
        prefix: str = "改写问题："
    ):
        """
        Initialize dataset.

        Args:
            data: List of training examples with input and target
            tokenizer: Tokenizer
            max_source_length: Maximum source length
            max_target_length: Maximum target length
            prefix: Prefix for input text
        """
        self.data = data
        self.tokenizer = tokenizer
        self.max_source_length = max_source_length
        self.max_target_length = max_target_length
        self.prefix = prefix

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        input_text = f"{self.prefix}{item['input']}"
        target_text = item['target']

        # Tokenize input
        input_encoding = self.tokenizer(
            input_text,
            max_length=self.max_source_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )

        # Tokenize target
        target_encoding = self.tokenizer(
            target_text,
            max_length=self.max_target_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )

        return {
            "input_ids": input_encoding["input_ids"].squeeze(0),
            "attention_mask": input_encoding["attention_mask"].squeeze(0),
            "labels": target_encoding["input_ids"].squeeze(0),
        }


class RewriteTrainer:
    """
    Trainer for T5-based question rewriting model.

    Example:
        >>> trainer = RewriteTrainer()
        >>> trainer.train("data/rewrite/train.jsonl", "models/rewrite_t5")
    """

    def __init__(
        self,
        config: Optional[T5Config] = None
    ):
        """
        Initialize trainer.

        Args:
            config: T5 configuration
        """
        self.config = config or T5Config()
        self.preprocessor = RewritePreprocessor()

        # Initialize tokenizer
        try:
            self.tokenizer = T5Tokenizer.from_pretrained(
                self.config.model_name,
                cache_dir=self.config.cache_dir
            )
        except Exception:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name,
                cache_dir=self.config.cache_dir
            )

        # Load training data
        self.train_data = None
        self.eval_data = None
        self.model = None

    def load_data(
        self,
        train_path: str,
        eval_path: Optional[str] = None
    ):
        """
        Load training and evaluation data.

        Args:
            train_path: Path to training data (JSONL format)
            eval_path: Path to evaluation data (optional)
        """
        self.train_data = self.preprocessor.load_jsonl(train_path)

        if eval_path:
            self.eval_data = self.preprocessor.load_jsonl(eval_path)

    def prepare_datasets(self):
        """Prepare PyTorch datasets."""
        if self.train_data is None:
            raise ValueError("No training data loaded. Call load_data() first.")

        self.train_dataset = RewriteDataset(
            self.train_data,
            self.tokenizer,
            self.config.max_source_length,
            self.config.max_target_length,
            self.config.generation_prefix
        )

        if self.eval_data:
            self.eval_dataset = RewriteDataset(
                self.eval_data,
                self.tokenizer,
                self.config.max_source_length,
                self.config.max_target_length,
                self.config.generation_prefix
            )
        else:
            self.eval_dataset = None

    def train(
        self,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Train the rewrite model.

        Args:
            output_dir: Output directory for model

        Returns:
            Training metrics
        """
        if output_dir is None:
            output_dir = self.config.output_dir

        # Prepare datasets
        self.prepare_datasets()

        # Initialize model
        self.model = T5ForConditionalGeneration.from_pretrained(
            self.config.model_name,
            cache_dir=self.config.cache_dir
        )

        # Data collator
        data_collator = DataCollatorForSeq2Seq(
            tokenizer=self.tokenizer,
            model=self.model
        )

        def compute_metrics(eval_preds):
            predictions, labels = eval_preds

            # Replace -100 in labels (ignore index)
            labels[labels == -100] = self.tokenizer.pad_token_id

            # Decode predictions and labels
            decoded_preds = self.tokenizer.batch_decode(
                predictions,
                skip_special_tokens=True
            )
            decoded_labels = self.tokenizer.batch_decode(
                labels,
                skip_special_tokens=True
            )

            # Simple accuracy: exact match
            exact_match = sum(
                1 for p, l in zip(decoded_preds, decoded_labels) if p.strip() == l.strip()
            ) / len(decoded_preds)

            # BLEU-like metric (word-level)
            from collections import Counter
            def bleu_score(pred, ref):
                pred_words = pred.split()
                ref_words = ref.split()
                if not pred_words:
                    return 0.0
                common = Counter(pred_words) & Counter(ref_words)
                return sum(common.values()) / len(pred_words)

            avg_bleu = sum(
                bleu_score(p, l) for p, l in zip(decoded_preds, decoded_labels)
            ) / len(decoded_preds)

            return {
                "exact_match": exact_match,
                "avg_bleu": avg_bleu,
            }

        # Training arguments
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=self.config.num_train_epochs,
            per_device_train_batch_size=self.config.batch_size,
            per_device_eval_batch_size=self.config.batch_size,
            learning_rate=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
            warmup_ratio=self.config.warmup_ratio,
            logging_dir=f"{output_dir}/logs",
            logging_steps=self.config.logging_steps,
            evaluation_strategy="steps" if self.eval_dataset else "no",
            eval_steps=self.config.eval_steps if self.eval_dataset else None,
            save_steps=self.config.save_steps,
            save_total_limit=3,
            load_best_model_at_end=True if self.eval_dataset else False,
            metric_for_best_model="avg_bleu" if self.eval_dataset else None,
            greater_is_better=True,
            report_to="tensorboard",
            predict_with_generate=True,
            generation_max_length=self.config.max_target_length,
            generation_num_beams=self.config.num_beams,
        )

        # Initialize trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=self.train_dataset,
            eval_dataset=self.eval_dataset,
            data_collator=data_collator,
            compute_metrics=compute_metrics if self.eval_dataset else None,
        )

        # Train
        train_result = trainer.train()

        # Save model
        trainer.save_model(output_dir)
        self.tokenizer.save_pretrained(output_dir)

        # Save metrics
        metrics = train_result.metrics
        trainer.log_metrics("train", metrics)
        trainer.save_metrics("train", metrics)

        return metrics

    def evaluate(self, test_path: str) -> Dict[str, Any]:
        """
        Evaluate the model on test data.

        Args:
            test_path: Path to test data

        Returns:
            Evaluation metrics
        """
        test_data = self.preprocessor.load_jsonl(test_path)

        test_dataset = RewriteDataset(
            test_data,
            self.tokenizer,
            self.config.max_source_length,
            self.config.max_target_length,
            self.config.generation_prefix
        )

        # Evaluate
        trainer = Trainer(model=self.model)
        metrics = trainer.evaluate(test_dataset)

        return metrics
