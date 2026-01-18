#!/usr/bin/env python
"""
Milvus initialization script.

This script initializes Milvus collection and imports data from Excel.
Run this script after setting up Milvus to prepare the vector database.

Usage:
    python scripts/init_milvus.py
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to import resume_agent module
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from tqdm import tqdm

from resume_agent.config import Config
from resume_agent.repositories import MilvusRepository
from resume_agent.embeddings import FlagEmbeddingService


def init_milvus_collection(config: Config) -> MilvusRepository:
    """
    Initialize Milvus collection with proper schema.

    Args:
        config: Config object with Milvus settings

    Returns:
        Initialized MilvusRepository
    """
    print(f"Initializing Milvus collection '{config.MILVUS_COLLECTION_NAME}'...")

    # Initialize embedding service to get dimension
    print(f"Loading embedding model: {config.EMBEDDING_MODEL_NAME}")
    embedding_service = FlagEmbeddingService(
        model_name=config.EMBEDDING_MODEL_NAME,
        device=config.EMBEDDING_DEVICE
    )

    # Get embedding dimension
    dimension = embedding_service.dimension
    print(f"Embedding dimension: {dimension}")

    # Create repository and collection
    repository = MilvusRepository(config)
    repository.create_collection(dimension)

    print(f"Collection '{config.MILVUS_COLLECTION_NAME}' created successfully.")
    print(f"  - Index type: {config.MILVUS_INDEX_TYPE}")
    print(f"  - Metric type: {config.MILVUS_METRIC_TYPE}")

    return repository


def import_excel_data(config: Config, repository: MilvusRepository) -> None:
    """
    Import data from Excel to Milvus.

    Args:
        config: Config object
        repository: MilvusRepository instance
    """
    print(f"\nImporting data from {config.EXCEL_FILE_PATH}...")

    # Load Excel data
    if not os.path.exists(config.EXCEL_FILE_PATH):
        raise FileNotFoundError(f"Excel file not found: {config.EXCEL_FILE_PATH}")

    df = pd.read_excel(config.EXCEL_FILE_PATH)
    print(f"Found {len(df)} rows in Excel file")

    # Initialize embedding service
    embedding_service = FlagEmbeddingService(
        model_name=config.EMBEDDING_MODEL_NAME,
        device=config.EMBEDDING_DEVICE,
        cache_dir=config.EMBEDDING_CACHE_DIR,
        enable_cache=config.ENABLE_EMBEDDING_CACHE
    )

    # Prepare data
    template_names = df['问题'].tolist()
    download_links = df['答案'].tolist()

    print(f"Generating embeddings for {len(template_names)} templates...")
    vectors = embedding_service.encode(template_names)
    print(f"Embeddings shape: {vectors.shape}")

    # Batch insert
    print("Inserting data into Milvus...")
    batch_size = 10
    for i in range(0, len(template_names), batch_size):
        batch_end = min(i + batch_size, len(template_names))
        batch_names = template_names[i:batch_end]
        batch_vectors = vectors[i:batch_end]
        batch_links = download_links[i:batch_end]

        repository.insert_batch(
            template_names=batch_names,
            vectors=batch_vectors,
            download_links=batch_links
        )
        print(f"  Inserted {batch_end}/{len(template_names)} records")

    # Flush to ensure data is persisted
    repository.flush()
    print("Data import completed!")


def verify_import(config: Config, repository: MilvusRepository) -> None:
    """
    Verify the imported data.

    Args:
        config: Config object
        repository: MilvusRepository instance
    """
    print("\nVerifying import...")

    info = repository.get_collection_info()
    print(f"Collection info:")
    print(f"  - Name: {info.get('name')}")
    print(f"  - Entities: {info.get('num_entities')}")

    # Test a search query - reuse cached embedding service
    print("\nTesting vector search...")
    embedding_service = FlagEmbeddingService(
        model_name=config.EMBEDDING_MODEL_NAME,
        device=config.EMBEDDING_DEVICE,
        cache_dir=config.EMBEDDING_CACHE_DIR,
        enable_cache=config.ENABLE_EMBEDDING_CACHE
    )

    test_query = "人事行政"
    query_vector = embedding_service.encode_query(test_query)
    results = repository.search(query_vector, top_k=3)

    print(f"Search query: '{test_query}'")
    print(f"Results:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['template_name']} (score: {result['score']:.4f})")


def main():
    """Main entry point."""
    print("=" * 60)
    print("Milvus Initialization Script")
    print("=" * 60)

    # Load config
    config = Config()

    # Print configuration
    print("\nConfiguration:")
    print(f"  Milvus host: {config.MILVUS_HOST}:{config.MILVUS_PORT}")
    print(f"  Collection: {config.MILVUS_COLLECTION_NAME}")
    print(f"  Embedding model: {config.EMBEDDING_MODEL_NAME}")
    print(f"  Device: {config.EMBEDDING_DEVICE}")
    print(f"  Excel file: {config.EXCEL_FILE_PATH}")

    try:
        # Initialize collection
        repository = init_milvus_collection(config)

        # Import data
        import_excel_data(config, repository)

        # Verify
        verify_import(config, repository)

        print("\n" + "=" * 60)
        print("Initialization completed successfully!")
        print("=" * 60)
        print("\nYou can now use vector search mode:")
        print("  export SEARCH_MODE=vector")
        print("  python resume_agent.py")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
