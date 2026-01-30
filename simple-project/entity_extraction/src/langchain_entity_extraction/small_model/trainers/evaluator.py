"""
Model Evaluator.

Utilities for evaluating trained models on test data.
"""

from typing import List, Dict, Any, Optional
import time

from datasets import load_metric
from tqdm import tqdm

from langchain_entity_extraction.small_model.models.ner_model import EntityRecognitionModel
from langchain_entity_extraction.small_model.models.seq2seq_model import QuestionRewriteModel


class ModelEvaluator:
    """
    Evaluator for small models.

    Provides comprehensive evaluation metrics for NER and Seq2Seq models.

    Example:
        >>> evaluator = ModelEvaluator()
        >>> metrics = evaluator.evaluate_ner(model, test_data)
    """

    def __init__(self):
        """Initialize evaluator."""
        self.ner_metric = load_metric("seqeval")

    def evaluate_ner(
        self,
        model: EntityRecognitionModel,
        test_data: List[Dict[str, Any]],
        return_predictions: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluate NER model.

        Args:
            model: Trained NER model
            test_data: Test data with text and entities
            return_predictions: Whether to return predictions

        Returns:
            Evaluation metrics
        """
        all_predictions = []
        all_labels = []
        results = []
        total_time = 0

        for item in tqdm(test_data, desc="Evaluating NER"):
            text = item["text"]
            true_entities = item.get("entities", [])

            # Time prediction
            start_time = time.time()
            pred_entities = model.predict(text)
            prediction_time = (time.time() - start_time) * 1000
            total_time += prediction_time

            # Convert to BIO labels for metric calculation
            # (simplified - would need proper implementation)
            pred_labels = ["O"] * len(text)  # Placeholder
            true_labels = ["O"] * len(text)  # Placeholder

            all_predictions.append(pred_labels)
            all_labels.append(true_labels)

            results.append({
                "text": text,
                "true_entities": true_entities,
                "pred_entities": pred_entities,
                "time_ms": prediction_time
            })

        # Calculate metrics
        metrics = {
            "avg_time_ms": total_time / len(test_data),
            "total_time_ms": total_time,
        }

        if return_predictions:
            metrics["predictions"] = results

        return metrics

    def evaluate_rewrite(
        self,
        model: QuestionRewriteModel,
        test_data: List[Dict[str, Any]],
        return_predictions: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluate rewrite model.

        Args:
            model: Trained rewrite model
            test_data: Test data with input and target
            return_predictions: Whether to return predictions

        Returns:
            Evaluation metrics
        """
        results = []
        total_time = 0
        exact_matches = 0

        for item in tqdm(test_data, desc="Evaluating Rewrite"):
            input_text = item["input"]
            target_text = item["target"]

            # Time prediction
            start_time = time.time()
            pred_text = model.rewrite(input_text)
            prediction_time = (time.time() - start_time) * 1000
            total_time += prediction_time

            # Check exact match
            is_exact = pred_text.strip() == target_text.strip()
            if is_exact:
                exact_matches += 1

            results.append({
                "input": input_text,
                "target": target_text,
                "prediction": pred_text,
                "exact_match": is_exact,
                "time_ms": prediction_time
            })

        metrics = {
            "exact_match_rate": exact_matches / len(test_data),
            "avg_time_ms": total_time / len(test_data),
            "total_time_ms": total_time,
        }

        if return_predictions:
            metrics["predictions"] = results

        return metrics

    def compare_models(
        self,
        small_model: Any,
        llm_results: List[Dict],
        test_data: List[Dict]
    ) -> Dict[str, Any]:
        """
        Compare small model with LLM results.

        Args:
            small_model: Trained small model
            llm_results: Results from LLM
            test_data: Test data

        Returns:
            Comparison metrics
        """
        small_results = []

        for item in tqdm(test_data, desc="Comparing models"):
            text = item.get("text") or item.get("input", "")

            if isinstance(small_model, EntityRecognitionModel):
                pred = small_model.predict(text)
            elif isinstance(small_model, QuestionRewriteModel):
                pred = small_model.rewrite(text)
            else:
                pred = None

            small_results.append(pred)

        # Compare
        agreement = sum(
            1 for s, l in zip(small_results, llm_results) if s == l
        ) / len(llm_results) if llm_results else 0

        return {
            "agreement_rate": agreement,
            "small_model_results": small_results,
            "llm_results": llm_results,
        }

    def benchmark_speed(
        self,
        model: Any,
        test_texts: List[str],
        num_runs: int = 10
    ) -> Dict[str, Any]:
        """
        Benchmark model speed.

        Args:
            model: Model to benchmark
            test_texts: Test texts
            num_runs: Number of runs for averaging

        Returns:
            Speed metrics
        """
        times = []

        for _ in range(num_runs):
            start_time = time.time()

            for text in test_texts:
                if isinstance(model, EntityRecognitionModel):
                    model.predict(text)
                elif isinstance(model, QuestionRewriteModel):
                    model.rewrite(text)

            elapsed = (time.time() - start_time) * 1000
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        return {
            "avg_time_ms": avg_time,
            "min_time_ms": min_time,
            "max_time_ms": max_time,
            "avg_per_item_ms": avg_time / len(test_texts),
            "items_per_second": len(test_texts) / (avg_time / 1000),
        }

    def print_report(self, metrics: Dict[str, Any], title: str = "Evaluation Report"):
        """Print a formatted evaluation report."""
        print(f"\n{'='*60}")
        print(f"{title}")
        print(f"{'='*60}")

        for key, value in metrics.items():
            if key == "predictions":
                continue
            if isinstance(value, float):
                print(f"{key}: {value:.4f}")
            else:
                print(f"{key}: {value}")

        print(f"{'='*60}\n")
