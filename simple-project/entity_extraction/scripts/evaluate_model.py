#!/usr/bin/env python
"""
Model Evaluation Script.

Evaluate trained models on test data.
"""

import argparse
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langchain_entity_extraction.small_model.trainers.evaluator import ModelEvaluator
from langchain_entity_extraction.small_model.models.ner_model import EntityRecognitionModel
from langchain_entity_extraction.small_model.models.seq2seq_model import QuestionRewriteModel
from langchain_entity_extraction.small_model.config.ner_config import NERConfig
from langchain_entity_extraction.small_model.config.t5_config import T5Config
from langchain_entity_extraction.small_model.preprocessors.ner_preprocessor import NERPreprocessor
from langchain_entity_extraction.small_model.preprocessors.rewrite_preprocessor import RewritePreprocessor


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained models")

    parser.add_argument(
        "--model_type",
        type=str,
        choices=["ner", "rewrite", "both"],
        default="both",
        help="Type of model to evaluate"
    )
    parser.add_argument(
        "--ner_model_path",
        type=str,
        default="models/ner_bert",
        help="Path to NER model"
    )
    parser.add_argument(
        "--rewrite_model_path",
        type=str,
        default="models/rewrite_t5",
        help="Path to Rewrite model"
    )
    parser.add_argument(
        "--ner_test_data",
        type=str,
        default="data/ner/test.jsonl",
        help="Path to NER test data"
    )
    parser.add_argument(
        "--rewrite_test_data",
        type=str,
        default="data/rewrite/test.jsonl",
        help="Path to Rewrite test data"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for results (JSON)"
    )

    args = parser.parse_args()

    evaluator = ModelEvaluator()

    results = {}

    # Evaluate NER model
    if args.model_type in ["ner", "both"]:
        print("=" * 60)
        print("Evaluating NER Model")
        print("=" * 60)

        ner_config = NERConfig()
        ner_model = EntityRecognitionModel(args.ner_model_path, ner_config)

        ner_preprocessor = NERPreprocessor()
        ner_test_data = ner_preprocessor.load_jsonl(args.ner_test_data)

        ner_metrics = evaluator.evaluate_ner(
            ner_model,
            ner_test_data,
            return_predictions=False
        )

        evaluator.print_report(ner_metrics, "NER Evaluation Results")
        results["ner"] = ner_metrics

    # Evaluate Rewrite model
    if args.model_type in ["rewrite", "both"]:
        print("\n" + "=" * 60)
        print("Evaluating Rewrite Model")
        print("=" * 60)

        t5_config = T5Config()
        rewrite_model = QuestionRewriteModel(args.rewrite_model_path, t5_config)

        rewrite_preprocessor = RewritePreprocessor()
        rewrite_test_data = rewrite_preprocessor.load_jsonl(args.rewrite_test_data)

        rewrite_metrics = evaluator.evaluate_rewrite(
            rewrite_model,
            rewrite_test_data,
            return_predictions=False
        )

        evaluator.print_report(rewrite_metrics, "Rewrite Evaluation Results")
        results["rewrite"] = rewrite_metrics

    # Save results if output specified
    if args.output:
        import json
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()
