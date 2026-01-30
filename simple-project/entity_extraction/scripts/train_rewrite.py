#!/usr/bin/env python
"""
Rewrite Model Training Script.

Train a T5-based question rewriting model.
"""

import argparse
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langchain_entity_extraction.small_model.trainers.rewrite_trainer import RewriteTrainer
from langchain_entity_extraction.small_model.config.t5_config import T5Config


def main():
    parser = argparse.ArgumentParser(description="Train Rewrite model")

    # Data arguments
    parser.add_argument(
        "--train_data",
        type=str,
        default="data/rewrite/train.jsonl",
        help="Path to training data"
    )
    parser.add_argument(
        "--eval_data",
        type=str,
        default=None,
        help="Path to evaluation data (optional)"
    )
    parser.add_argument(
        "--test_data",
        type=str,
        default=None,
        help="Path to test data for evaluation"
    )

    # Model arguments
    parser.add_argument(
        "--model_name",
        type=str,
        default="uer/t5-small",
        help="Pre-trained model name"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="models/rewrite_t5",
        help="Output directory for trained model"
    )

    # Training arguments
    parser.add_argument(
        "--num_epochs",
        type=int,
        default=5,
        help="Number of training epochs"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=8,
        help="Batch size"
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=3e-4,
        help="Learning rate"
    )
    parser.add_argument(
        "--warmup_ratio",
        type=float,
        default=0.1,
        help="Warmup ratio"
    )
    parser.add_argument(
        "--max_source_length",
        type=int,
        default=128,
        help="Maximum source length"
    )
    parser.add_argument(
        "--max_target_length",
        type=int,
        default=128,
        help="Maximum target length"
    )

    # Other arguments
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Device to use (cuda/cpu)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed"
    )

    args = parser.parse_args()

    # Set random seed
    import torch
    import random
    import numpy as np

    torch.manual_seed(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)

    # Create config
    config = T5Config(
        model_name=args.model_name,
        max_source_length=args.max_source_length,
        max_target_length=args.max_target_length,
        num_train_epochs=args.num_epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        warmup_ratio=args.warmup_ratio,
        output_dir=args.output_dir,
    )

    if args.device:
        config.device = args.device

    print("=" * 60)
    print("Rewrite Model Training")
    print("=" * 60)
    print(f"Model: {args.model_name}")
    print(f"Train data: {args.train_data}")
    print(f"Output dir: {args.output_dir}")
    print(f"Epochs: {args.num_epochs}")
    print(f"Batch size: {args.batch_size}")
    print(f"Learning rate: {args.learning_rate}")
    print(f"Device: {config.device}")
    print("=" * 60)

    # Initialize trainer
    trainer = RewriteTrainer(config=config)

    # Load data
    print("\nLoading data...")
    trainer.load_data(args.train_data, args.eval_data)

    # Train
    print("\nStarting training...")
    metrics = trainer.train(args.output_dir)

    print("\nTraining completed!")
    print("Final metrics:")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")

    # Evaluate on test data if provided
    if args.test_data:
        print(f"\nEvaluating on test data: {args.test_data}")
        test_metrics = trainer.evaluate(args.test_data)
        print("Test metrics:")
        for key, value in test_metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")

    print(f"\nModel saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
