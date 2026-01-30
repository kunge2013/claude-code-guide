#!/usr/bin/env python
"""
Data Generation Script.

Generate synthetic training data for MVP development.
"""

import argparse
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langchain_entity_extraction.small_model.preprocessors.data_augmentation import DataAugmentation
from langchain_entity_extraction.small_model.preprocessors.ner_preprocessor import NERPreprocessor
from langchain_entity_extraction.small_model.preprocessors.rewrite_preprocessor import RewritePreprocessor


def main():
    parser = argparse.ArgumentParser(description="Generate training data")

    parser.add_argument(
        "--ner_count",
        type=int,
        default=1000,
        help="Number of NER samples to generate"
    )
    parser.add_argument(
        "--rewrite_count",
        type=int,
        default=500,
        help="Number of rewrite samples to generate"
    )
    parser.add_argument(
        "--augment_ratio",
        type=float,
        default=0.5,
        help="Ratio of augmented data to generate"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="data",
        help="Output directory for generated data"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Training Data Generation")
    print("=" * 60)
    print(f"NER samples: {args.ner_count}")
    print(f"Rewrite samples: {args.rewrite_count}")
    print(f"Augment ratio: {args.augment_ratio}")
    print(f"Output dir: {args.output_dir}")
    print("=" * 60)

    # Initialize augmenter
    augmenter = DataAugmentation()

    # Generate NER data
    print(f"\nGenerating {args.ner_count} NER samples...")
    ner_data = augmenter.generate_ner_data(args.ner_count)

    # Augment NER data
    if args.augment_ratio > 0:
        print(f"Augmenting NER data (ratio: {args.augment_ratio})...")
        ner_data = augmenter.augment_with_synonyms(ner_data, args.augment_ratio)

    # Save NER data
    os.makedirs(f"{args.output_dir}/ner", exist_ok=True)
    ner_preprocessor = NERPreprocessor()

    # Split into train/dev
    train_ner, dev_ner = ner_preprocessor.split_train_dev(ner_data, dev_ratio=0.1)

    ner_preprocessor.save_jsonl(train_ner, f"{args.output_dir}/ner/train.jsonl")
    ner_preprocessor.save_jsonl(dev_ner, f"{args.output_dir}/ner/dev.jsonl")

    # Generate test data (smaller set)
    test_ner = augmenter.generate_ner_data(args.ner_count // 10)
    ner_preprocessor.save_jsonl(test_ner, f"{args.output_dir}/ner/test.jsonl")

    print(f"NER data saved:")
    print(f"  Train: {len(train_ner)} samples")
    print(f"  Dev: {len(dev_ner)} samples")
    print(f"  Test: {len(test_ner)} samples")

    # Generate Rewrite data
    print(f"\nGenerating {args.rewrite_count} rewrite samples...")
    rewrite_data = augmenter.generate_rewrite_data(args.rewrite_count)

    # Save Rewrite data
    os.makedirs(f"{args.output_dir}/rewrite", exist_ok=True)
    rewrite_preprocessor = RewritePreprocessor()

    # Split into train/dev
    train_rewrite, dev_rewrite = rewrite_preprocessor.split_train_dev(rewrite_data, dev_ratio=0.1)

    rewrite_preprocessor.save_jsonl(train_rewrite, f"{args.output_dir}/rewrite/train.jsonl")
    rewrite_preprocessor.save_jsonl(dev_rewrite, f"{args.output_dir}/rewrite/dev.jsonl")

    # Generate test data
    test_rewrite = augmenter.generate_rewrite_data(args.rewrite_count // 10)
    rewrite_preprocessor.save_jsonl(test_rewrite, f"{args.output_dir}/rewrite/test.jsonl")

    print(f"Rewrite data saved:")
    print(f"  Train: {len(train_rewrite)} samples")
    print(f"  Dev: {len(dev_rewrite)} samples")
    print(f"  Test: {len(test_rewrite)} samples")

    # Print statistics
    print("\n" + "=" * 60)
    print("Data Statistics")
    print("=" * 60)

    ner_stats = ner_preprocessor.get_statistics(train_ner)
    print(f"\nNER Train Statistics:")
    print(f"  Total samples: {ner_stats['total_samples']}")
    print(f"  Total entities: {ner_stats['total_entities']}")
    print(f"  Avg entities/sample: {ner_stats['avg_entities_per_sample']:.2f}")
    print(f"  Entity types: {ner_stats['entity_types']}")

    rewrite_stats = rewrite_preprocessor.get_statistics(train_rewrite)
    print(f"\nRewrite Train Statistics:")
    print(f"  Total samples: {rewrite_stats['total_samples']}")
    print(f"  Avg input length: {rewrite_stats['avg_input_length']:.2f}")
    print(f"  Avg target length: {rewrite_stats['avg_target_length']:.2f}")

    print("\n" + "=" * 60)
    print("Data generation completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
