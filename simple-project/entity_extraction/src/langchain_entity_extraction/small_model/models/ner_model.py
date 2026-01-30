"""
BERT-based Named Entity Recognition Model.

Implements a BERT-based sequence labeling model for entity extraction.
"""

import os
from typing import List, Dict, Any, Optional, Tuple

import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForTokenClassification


class EntityRecognitionModel:
    """
    BERT-based Named Entity Recognition model.

    Loads a pre-trained BERT model fine-tuned for NER tasks
    and provides methods for entity prediction.

    Example:
        >>> from langchain_entity_extraction.small_model.config import NERConfig
        >>> from langchain_entity_extraction.small_model.models import EntityRecognitionModel
        >>>
        >>> config = NERConfig()
        >>> model = EntityRecognitionModel("models/ner_bert", config)
        >>> entities = model.predict("今年cdn产品金额是多少")
    """

    def __init__(
        self,
        model_path: str,
        config: Optional["NERConfig"] = None,
        device: Optional[str] = None
    ):
        """
        Initialize the NER model.

        Args:
            model_path: Path to the trained model (or HuggingFace model name)
            config: NERConfig object (optional, will use defaults if not provided)
            device: Device to use ("cuda", "cpu", or None for auto)
        """
        from langchain_entity_extraction.small_model.config.ner_config import NERConfig
        from langchain_entity_extraction.small_model.utils.model_utils import ModelUtils
        from langchain_entity_extraction.small_model.utils.bio_utils import BioUtils

        self.config = config or NERConfig()
        self.device = ModelUtils.get_device(device)
        self.bio_utils = BioUtils()

        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            cache_dir=self.config.cache_dir,
            use_fast=True
        )

        self.model = AutoModelForTokenClassification.from_pretrained(
            model_path,
            cache_dir=self.config.cache_dir,
            num_labels=self.config.num_labels
        )

        # Move model to device
        self.model.to(self.device)
        self.model.eval()  # Set to evaluation mode

        # Label mappings
        self.label_list = self.config.label_list
        self.label2id = self.config.get_label2id()
        self.id2label = self.config.get_id2label()

    def predict(
        self,
        text: str,
        return_confidence: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Predict entities in the given text.

        Args:
            text: Input text
            return_confidence: Whether to return confidence scores

        Returns:
            List of entity dicts with keys:
                - entity: the entity text
                - label: entity type (PRODUCT, TIME, FIELD, etc.)
                - start: start character index
                - end: end character index
                - confidence: confidence score (if return_confidence=True)
        """
        with torch.no_grad():
            # Tokenize
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=self.config.max_seq_length,
                padding="max_length"
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Get predictions
            outputs = self.model(**inputs)
            logits = outputs.logits

            # Get predicted labels
            predictions = torch.argmax(logits, dim=-1)[0].cpu().numpy()

            # Get input IDs (to filter out padding and special tokens)
            input_ids = inputs["input_ids"][0].cpu().numpy()
            attention_mask = inputs["attention_mask"][0].cpu().numpy()

            # Get confidence scores (max softmax probability)
            if return_confidence:
                probs = torch.softmax(logits, dim=-1)[0]
                confidences = torch.max(probs, dim=-1)[0].cpu().numpy()

        # Convert to entities
        entities = []
        current_entity = None

        # Track character offsets
        char_offset = 0

        for i, (pred_id, mask_val) in enumerate(zip(predictions, attention_mask)):
            if mask_val == 0:
                # Padding token
                break

            # Skip special tokens
            token_id = input_ids[i]
            if token_id in [self.tokenizer.cls_token_id, self.tokenizer.sep_token_id]:
                continue

            # Get label
            label = self.id2label[pred_id]

            # Get token text (decode single token)
            token_text = self.tokenizer.decode([token_id], skip_special_tokens=True)

            # Calculate character offsets
            # Note: This is a simplified approach; for accurate offsets,
            # you would need to use tokenizer's offset mapping
            if char_offset == 0:
                start = 0
            else:
                start = char_offset + 1  # +1 for space

            end = start + len(token_text)
            char_offset = end

            if self.bio_utils.is_b_tag(label):
                # Save previous entity
                if current_entity:
                    entities.append(current_entity)

                # Start new entity
                entity_type = self.bio_utils.get_entity_type(label)
                current_entity = {
                    "entity": token_text,
                    "label": entity_type,
                    "start": start,
                    "end": end,
                }
                if return_confidence:
                    current_entity["confidence"] = float(confidences[i])

            elif self.bio_utils.is_i_tag(label) and current_entity:
                # Continue current entity
                entity_type = self.bio_utils.get_entity_type(label)
                if entity_type == current_entity["label"]:
                    current_entity["entity"] += token_text
                    current_entity["end"] = end
                else:
                    # Mismatched entity type, end current and start new
                    entities.append(current_entity)
                    current_entity = {
                        "entity": token_text,
                        "label": entity_type,
                        "start": start,
                        "end": end,
                    }
                    if return_confidence:
                        current_entity["confidence"] = float(confidences[i])
            else:
                # O tag or mismatched I tag
                if current_entity:
                    entities.append(current_entity)
                    current_entity = None

        # Don't forget the last entity
        if current_entity:
            entities.append(current_entity)

        return entities

    def predict_batch(
        self,
        texts: List[str],
        return_confidence: bool = False
    ) -> List[List[Dict[str, Any]]]:
        """
        Predict entities for multiple texts.

        Args:
            texts: List of input texts
            return_confidence: Whether to return confidence scores

        Returns:
            List of entity lists (one per input text)
        """
        results = []
        for text in texts:
            entities = self.predict(text, return_confidence=return_confidence)
            results.append(entities)
        return results

    def get_confidence(self, text: str) -> float:
        """
        Get overall confidence score for prediction on text.

        Args:
            text: Input text

        Returns:
            Confidence score between 0 and 1
        """
        entities = self.predict(text, return_confidence=True)

        if not entities:
            return 0.0

        # Return average confidence
        confidences = [e.get("confidence", 0.0) for e in entities]
        return sum(confidences) / len(confidences)

    def predict_with_offsets(
        self,
        text: str
    ) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
        """
        Predict entities with token-level information.

        Args:
            text: Input text

        Returns:
            Tuple of (entities, tokens, labels)
        """
        with torch.no_grad():
            # Tokenize
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=self.config.max_seq_length,
                padding="max_length",
                return_offsets_mapping=True
            )

            # Move to device
            input_ids = inputs["input_ids"].to(self.device)
            attention_mask = inputs["attention_mask"].to(self.device)

            # Get predictions
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            predictions = torch.argmax(outputs.logits, dim=-1)[0].cpu().numpy()

            # Get tokens and offsets
            tokens = []
            labels = []
            offsets = inputs.get("offset_mapping", [])

            for i, (pred_id, mask_val) in enumerate(zip(predictions, attention_mask[0].cpu().numpy())):
                if mask_val == 0:
                    break

                token_id = input_ids[0][i].cpu().item()
                if token_id in [self.tokenizer.cls_token_id, self.tokenizer.sep_token_id]:
                    continue

                token_text = self.tokenizer.decode([token_id], skip_special_tokens=True)
                label = self.id2label[pred_id]

                tokens.append(token_text)
                labels.append(label)

            entities = self.bio_utils.bio_tags_to_entities(tokens, labels)

            return entities, tokens, labels


class SimpleBERTNER(nn.Module):
    """
    Simple BERT NER model implementation for training.

    This is a minimal implementation that can be used for training
    a custom NER model on specific data.
    """

    def __init__(
        self,
        model_name: str = "hfl/chinese-bert-wwm-ext",
        num_labels: int = 13,
        dropout: float = 0.1
    ):
        """
        Initialize the model.

        Args:
            model_name: Pre-trained BERT model name
            num_labels: Number of entity labels
            dropout: Dropout rate
        """
        super().__init__()

        from transformers import AutoModel

        self.bert = AutoModel.from_pretrained(model_name)
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(self.bert.config.hidden_size, num_labels)

    def forward(self, input_ids, attention_mask=None, labels=None):
        """
        Forward pass.

        Args:
            input_ids: Input token IDs
            attention_mask: Attention mask
            labels: Optional labels for computing loss

        Returns:
            Dict with loss (if labels provided) and logits
        """
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        sequence_output = outputs.last_hidden_state

        sequence_output = self.dropout(sequence_output)
        logits = self.classifier(sequence_output)

        loss = None
        if labels is not None:
            import torch.nn.functional as F
            loss_fct = nn.CrossEntropyLoss(ignore_index=-100)
            loss = loss_fct(
                logits.view(-1, self.classifier.out_features),
                labels.view(-1)
            )

        return {"loss": loss, "logits": logits}
