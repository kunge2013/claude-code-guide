"""
Rewrite Data Preprocessor.

Data preprocessing utilities for Seq2Seq model training.
"""

import json
from typing import List, Dict, Any, Optional


class RewritePreprocessor:
    """
    Preprocessor for question rewriting training data.

    Handles loading and preprocessing of JSONL format data.

    Example:
        >>> preprocessor = RewritePreprocessor()
        >>> data = preprocessor.load_jsonl("data/rewrite/train.jsonl")
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
            if "input" not in item or "target" not in item:
                continue

            processed_item = {
                "input": item["input"],
                "target": item["target"]
            }

            # Optional entities field
            if "entities" in item:
                processed_item["entities"] = item["entities"]

            processed.append(processed_item)

        return processed

    def validate_sample(self, sample: Dict) -> bool:
        """
        Validate a training sample.

        Args:
            sample: Sample dict

        Returns:
            True if valid
        """
        required_fields = ["input", "target"]
        for field in required_fields:
            if field not in sample:
                return False
            if not sample[field] or not sample[field].strip():
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
        input_lengths = []
        target_lengths = []

        for item in data:
            input_text = item.get("input", "")
            target_text = item.get("target", "")

            input_lengths.append(len(input_text))
            target_lengths.append(len(target_text))

        return {
            "total_samples": total,
            "avg_input_length": sum(input_lengths) / len(input_lengths) if input_lengths else 0,
            "max_input_length": max(input_lengths) if input_lengths else 0,
            "min_input_length": min(input_lengths) if input_lengths else 0,
            "avg_target_length": sum(target_lengths) / len(target_lengths) if target_lengths else 0,
            "max_target_length": max(target_lengths) if target_lengths else 0,
            "min_target_length": min(target_lengths) if target_lengths else 0,
        }
