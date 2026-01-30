"""
Model Utilities.

Utility functions for loading and managing models.
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path


class ModelUtils:
    """Utilities for model management."""

    @staticmethod
    def get_device(device: Optional[str] = None) -> str:
        """
        Get the appropriate device for model inference.

        Args:
            device: User-specified device ("cuda", "cpu", or None for auto)

        Returns:
            Device string ("cuda" or "cpu")
        """
        if device == "cpu":
            return "cpu"

        try:
            import torch
            if device == "cuda" or device is None:
                if torch.cuda.is_available():
                    return "cuda"
        except ImportError:
            pass

        return "cpu"

    @staticmethod
    def ensure_dir(path: str) -> str:
        """
        Ensure directory exists, create if not.

        Args:
            path: Directory path

        Returns:
            The path (for convenience)
        """
        Path(path).mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def get_model_size(model_path: str) -> Dict[str, Any]:
        """
        Get model size information.

        Args:
            model_path: Path to model directory

        Returns:
            Dict with size information (in MB)
        """
        total_size = 0
        file_count = 0

        for root, _, files in os.walk(model_path):
            for file in files:
                file_path = os.path.join(root, file)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
                    file_count += 1

        return {
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count,
            "path": model_path,
        }

    @staticmethod
    def load_label_file(label_path: str) -> list:
        """
        Load labels from a text file (one per line).

        Args:
            label_path: Path to label file

        Returns:
            List of label strings
        """
        labels = []
        with open(label_path, "r", encoding="utf-8") as f:
            for line in f:
                label = line.strip()
                if label:
                    labels.append(label)
        return labels

    @staticmethod
    def save_label_file(labels: list, label_path: str) -> None:
        """
        Save labels to a text file (one per line).

        Args:
            labels: List of label strings
            label_path: Path to save label file
        """
        with open(label_path, "w", encoding="utf-8") as f:
            for label in labels:
                f.write(f"{label}\n")

    @staticmethod
    def format_time(seconds: float) -> str:
        """
        Format seconds into human-readable string.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted string like "1h 23m 45s"
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            minutes = (seconds % 3600) / 60
            return f"{int(hours)}h {int(minutes)}m"

    @staticmethod
    def get_model_info(model) -> Dict[str, Any]:
        """
        Get information about a model.

        Args:
            model: A PyTorch or Transformers model

        Returns:
            Dict with model information
        """
        info = {
            "model_type": type(model).__name__,
        }

        try:
            import torch
            if hasattr(model, "num_parameters"):
                info["num_parameters"] = model.num_parameters()
            else:
                info["num_parameters"] = sum(
                    p.numel() for p in model.parameters()
                )

            # Calculate in MB
            info["size_mb"] = round(
                sum(p.numel() * p.element_size() for p in model.parameters()) / (1024 * 1024),
                2
            )
        except ImportError:
            pass

        return info

    @staticmethod
    def merge_configs(base_config: Dict, override_config: Dict) -> Dict:
        """
        Merge two configuration dicts (override takes precedence).

        Args:
            base_config: Base configuration
            override_config: Override configuration

        Returns:
            Merged configuration
        """
        result = base_config.copy()
        for key, value in override_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ModelUtils.merge_configs(result[key], value)
            else:
                result[key] = value
        return result
