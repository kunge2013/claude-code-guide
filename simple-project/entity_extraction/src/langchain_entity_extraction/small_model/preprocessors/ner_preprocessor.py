"""
NER Data Preprocessor.

Data preprocessing utilities for NER model training.
"""

import json
from typing import List, Dict, Any, Optional


class NERPreprocessor:
    """
    Preprocessor for NER training data.

    Handles loading and preprocessing of JSONL format data.

    Example:
        >>> preprocessor = NERPreprocessor()
        >>> data = preprocessor.load_jsonl("data/ner/train.jsonl")
        >>> processed = preprocessor.preprocess(data)
    """

    def load_jsonl(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Load data from JSONL file.

        Args:
            filepath: Path to JSONL file

        Returns:
            List of data items
        """
        data = []

        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    item = json.loads(line)
                    data.append(item)

        return data

    def save_jsonl(
        self,
        data: List[Dict[str, Any]],
        filepath: str
    ):
        """
        Save data to JSONL file.

        Args:
            data: Data to save
            filepath: Output file path
        """
        with open(filepath, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def preprocess(self, data: List[Dict]) -> List[Dict]:
        """
        Preprocess data for training.

        Args:
            data: Raw data

        Returns:
            Preprocessed data
        """
        processed = []

        for item in data:
            # Validate required fields
            if "text" not in item:
                continue

            processed_item = {
                "text": item["text"],
                "entities": item.get("entities", [])
            }

            processed.append(processed_item)

        return processed

    def validate_entity(
        self,
        entity: Dict[str, Any],
        text: str
    ) -> bool:
        """
        Validate entity annotation.

        Args:
            entity: Entity dict
            text: Original text

        Returns:
            True if valid
        """
        required_fields = ["entity", "label"]
        for field in required_fields:
            if field not in entity:
                return False

        # Check if entity text is in the original text
        if entity["entity"] not in text:
            return False

        # Validate label format
        label = entity["label"]
        if "-" in label:
            prefix, entity_type = label.split("-", 1)
            if prefix not in ["B", "I"]:
                return False

        return True

    def split_train_dev(
        self,
        data: List[Dict],
        dev_ratio: float = 0.1,
        shuffle: bool = True
    ) -> tuple[List[Dict], List[Dict]]:
        """
        Split data into train and dev sets.

        Args:
            data: Full dataset
            dev_ratio: Ratio for dev set
            shuffle: Whether to shuffle before splitting

        Returns:
            Tuple of (train_data, dev_data)
        """
        import random
        import copy

        if shuffle:
            data = copy.deepcopy(data)
            random.shuffle(data)

        split_idx = int(len(data) * (1 - dev_ratio))
        train_data = data[:split_idx]
        dev_data = data[split_idx:]

        return train_data, dev_data

    def get_statistics(
        self,
        data: List[Dict]
    ) -> Dict[str, Any]:
        """
        Get dataset statistics.

        Args:
            data: Dataset

        Returns:
            Statistics dict
        """
        total = len(data)
        total_entities = 0
        entity_types = {}
        text_lengths = []

        for item in data:
            text = item.get("text", "")
            entities = item.get("entities", [])

            text_lengths.append(len(text))
            total_entities += len(entities)

            for entity in entities:
                label = entity.get("label", "UNKNOWN")
                entity_types[label] = entity_types.get(label, 0) + 1

        return {
            "total_samples": total,
            "total_entities": total_entities,
            "avg_entities_per_sample": total_entities / total if total > 0 else 0,
            "entity_types": entity_types,
            "avg_text_length": sum(text_lengths) / len(text_lengths) if text_lengths else 0,
            "max_text_length": max(text_lengths) if text_lengths else 0,
            "min_text_length": min(text_lengths) if text_lengths else 0,
        }
