"""
NER Model Trainer.

Training script for BERT-based NER model.
"""

import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification
)
from datasets import load_metric

from langchain_entity_extraction.small_model.config.ner_config import NERConfig
from langchain_entity_extraction.small_model.preprocessors.ner_preprocessor import NERPreprocessor


class NERDataset(Dataset):
    """Dataset for NER training."""

    def __init__(
        self,
        data: List[Dict],
        tokenizer: Any,
        label2id: Dict[str, int],
        max_length: int = 128
    ):
        """
        Initialize dataset.

        Args:
            data: List of training examples with text and entities
            tokenizer: Tokenizer
            label2id: Label to ID mapping
            max_length: Maximum sequence length
        """
        self.data = data
        self.tokenizer = tokenizer
        self.label2id = label2id
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]
        text = item["text"]
        entities = item.get("entities", [])

        # Tokenize and get labels
        encoding = self._prepare_labels(text, entities)

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "labels": encoding["labels"].squeeze(0),
        }

    def _prepare_labels(self, text: str, entities: List[Dict]) -> Dict:
        """
        Prepare labels for NER.

        Args:
            text: Input text
            entities: List of entities

        Returns:
            Encoded inputs with labels
        """
        # Tokenize
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )

        # Initialize labels with -100 (ignore index)
        labels = torch.full_like(encoding["input_ids"], -100)

        # Convert entities to BIO labels
        # Note: This is simplified - proper implementation would use token offsets
        tokens = self.tokenizer.convert_ids_to_tokens(encoding["input_ids"][0])

        for i, token in enumerate(tokens):
            if token in [self.tokenizer.cls_token, self.tokenizer.sep_token, self.tokenizer.pad_token]:
                continue

            # Check if this token belongs to an entity
            labels[0, i] = self.label2id["O"]  # Default to O

        # Simple entity mapping (would need proper offset handling in production)
        for entity in entities:
            entity_text = entity["entity"]
            entity_label = entity["label"]
            b_label = f"B-{entity_label}"
            i_label = f"I-{entity_label}"

            # Find tokens matching entity
            for i, token in enumerate(tokens):
                if entity_text in token:
                    labels[0, i] = self.label2id.get(b_label, self.label2id["O"])

        encoding["labels"] = labels
        return encoding


class NERTrainer:
    """
    Trainer for BERT-based NER model.

    Example:
        >>> trainer = NERTrainer()
        >>> trainer.train("data/ner/train.jsonl", "models/ner_bert")
    """

    def __init__(
        self,
        config: Optional[NERConfig] = None
    ):
        """
        Initialize trainer.

        Args:
            config: NER configuration
        """
        self.config = config or NERConfig()
        self.preprocessor = NERPreprocessor()

        # Initialize tokenizer
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

        label2id = self.config.get_label2id()

        self.train_dataset = NERDataset(
            self.train_data,
            self.tokenizer,
            label2id,
            self.config.max_seq_length
        )

        if self.eval_data:
            self.eval_dataset = NERDataset(
                self.eval_data,
                self.tokenizer,
                label2id,
                self.config.max_seq_length
            )
        else:
            self.eval_dataset = None

    def train(
        self,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Train the NER model.

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
        self.model = AutoModelForTokenClassification.from_pretrained(
            self.config.model_name,
            num_labels=self.config.num_labels,
            id2label=self.config.get_id2label(),
            label2id=self.config.get_label2id(),
            cache_dir=self.config.cache_dir
        )

        # Data collator
        data_collator = DataCollatorForTokenClassification(
            tokenizer=self.tokenizer
        )

        # Metric
        metric = load_metric("seqeval")

        def compute_metrics(eval_preds):
            predictions, labels = eval_preds
            predictions = predictions.argmax(axis=-1)

            # Remove -100 labels and convert to label strings
            true_predictions = [
                [self.config.label_list[p] for p, l in zip(prediction, label) if l != -100]
                for prediction, label in zip(predictions, labels)
            ]
            true_labels = [
                [self.config.label_list[l] for p, l in zip(prediction, label) if l != -100]
                for prediction, label in zip(predictions, labels)
            ]

            results = metric.compute(predictions=true_predictions, references=true_labels)
            return {
                "precision": results["overall_precision"],
                "recall": results["overall_recall"],
                "f1": results["overall_f1"],
                "accuracy": results["overall_accuracy"],
            }

        # Training arguments
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=self.config.num_train_epochs,
            per_device_train_batch_size=self.config.batch_size,
            per_device_eval_batch_size=self.config.batch_size,
            learning_rate=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
            warmup_steps=self.config.warmup_steps,
            logging_dir=f"{output_dir}/logs",
            logging_steps=self.config.logging_steps,
            evaluation_strategy="steps" if self.eval_dataset else "no",
            eval_steps=self.config.eval_steps if self.eval_dataset else None,
            save_steps=self.config.save_steps,
            save_total_limit=3,
            load_best_model_at_end=True if self.eval_dataset else False,
            metric_for_best_model="f1" if self.eval_dataset else None,
            greater_is_better=True,
            report_to="tensorboard",
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
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

        label2id = self.config.get_label2id()
        test_dataset = NERDataset(
            test_data,
            self.tokenizer,
            label2id,
            self.config.max_seq_length
        )

        metric = load_metric("seqeval")

        # Evaluate
        trainer = Trainer(model=self.model)
        metrics = trainer.evaluate(test_dataset)

        return metrics
