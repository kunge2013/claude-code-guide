"""
Milvus repository for vector-based knowledge base storage.

This module provides a data access layer for Milvus vector database,
handling collection creation, data insertion, and vector similarity search.
"""
from typing import List, Dict, Any, Optional
import time

import numpy as np


class MilvusRepository:
    """
    Repository for Milvus vector database operations.

    Handles connection to Milvus, collection management, and vector search.
    """

    def __init__(self, config):
        """
        Initialize Milvus repository.

        Args:
            config: Config object with Milvus connection settings
        """
        self.config = config
        self._connections = None
        self._collection = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Milvus server."""
        try:
            from pymilvus import connections
        except ImportError:
            raise ImportError(
                "pymilvus is required for vector search. "
                "Install it with: pip install pymilvus"
            )

        connections.connect(
            alias="default",
            host=self.config.MILVUS_HOST,
            port=self.config.MILVUS_PORT
        )
        self._connections = connections

    @property
    def collection(self):
        """Lazy load the Milvus collection."""
        if self._collection is None:
            from pymilvus import Collection

            if self._has_collection():
                self._collection = Collection(self.config.MILVUS_COLLECTION_NAME)
                self._collection.load()
            else:
                raise ValueError(
                    f"Collection '{self.config.MILVUS_COLLECTION_NAME}' does not exist. "
                    f"Run init_milvus.py script first."
                )
        return self._collection

    def _has_collection(self) -> bool:
        """Check if the collection exists."""
        from pymilvus import utility

        return utility.has_collection(
            self.config.MILVUS_COLLECTION_NAME
        )

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        expr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            expr: Optional filter expression

        Returns:
            List of search results with template_name, download_link, and score
        """
        # Ensure collection is loaded before search
        collection = self.collection
        collection.load()

        search_params = {
            "metric_type": self.config.MILVUS_METRIC_TYPE,
            "params": {"nprobe": 16}
        }

        results = collection.search(
            data=[query_vector.tolist()],
            anns_field="template_name_vector",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["template_name", "download_link"]
        )

        # Format results
        formatted_results = []
        for hit in results[0]:
            formatted_results.append({
                "template_name": hit.entity.get("template_name"),
                "download_link": hit.entity.get("download_link"),
                "score": float(hit.score),
                "distance": float(hit.distance)
            })

        return formatted_results

    def insert(
        self,
        template_name: str,
        template_name_vector: np.ndarray,
        download_link: str,
        **metadata
    ) -> None:
        """
        Insert a single template into the collection.

        Args:
            template_name: Name of the template
            template_name_vector: Embedding vector for the template name
            download_link: Download link for the template
            **metadata: Additional metadata fields
        """
        # Use the collection property to ensure consistent collection access
        collection = self.collection

        data = [{
            "template_name": template_name,
            "template_name_vector": template_name_vector.tolist(),
            "download_link": download_link,
            **metadata
        }]

        collection.insert(data)

    def insert_batch(
        self,
        template_names: List[str],
        vectors: np.ndarray,
        download_links: List[str],
        **metadata
    ) -> None:
        """
        Batch insert templates into the collection.

        Args:
            template_names: List of template names
            vectors: Embedding vectors (numpy array)
            download_links: List of download links
            **metadata: Additional metadata (will be applied to all records)
        """
        # Use the collection property to ensure consistent collection access
        collection = self.collection

        # Ensure vectors is 2D
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)

        data = []
        for i, (name, vector, link) in enumerate(
            zip(template_names, vectors, download_links)
        ):
            record = {
                "id": i + 1,  # Simple ID generation
                "template_name": name,
                "template_name_vector": vector.tolist(),
                "download_link": link,
                **metadata
            }
            data.append(record)

        collection.insert(data)

    def create_collection(self, dimension: int) -> None:
        """
        Create a new Milvus collection for resume templates.

        Args:
            dimension: Dimension of the embedding vectors
        """
        from pymilvus import (
            Collection,
            CollectionSchema,
            DataType,
            FieldSchema,
            utility
        )

        # Drop existing collection if it exists
        if utility.has_collection(self.config.MILVUS_COLLECTION_NAME):
            utility.drop_collection(self.config.MILVUS_COLLECTION_NAME)

        # Define fields
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=False),
            FieldSchema(name="template_name", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(name="template_name_vector", dtype=DataType.FLOAT_VECTOR, dim=dimension),
            FieldSchema(name="download_link", dtype=DataType.VARCHAR, max_length=1024),
        ]

        # Create schema
        schema = CollectionSchema(
            fields=fields,
            description="Resume template knowledge base",
            enable_dynamic_field=True
        )

        # Create collection
        collection = Collection(
            name=self.config.MILVUS_COLLECTION_NAME,
            schema=schema
        )

        # Create index
        index_params = {
            "index_type": self.config.MILVUS_INDEX_TYPE,
            "metric_type": self.config.MILVUS_METRIC_TYPE,
            "params": {"nlist": 128}
        }

        collection.create_index(
            field_name="template_name_vector",
            index_params=index_params
        )

        self._collection = collection

    def flush(self) -> None:
        """Flush pending data to disk."""
        if self._collection:
            self._collection.flush()

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        from pymilvus import utility, Collection

        if not self._has_collection():
            return {"exists": False}

        collection = Collection(self.config.MILVUS_COLLECTION_NAME)
        stats = {
            "exists": True,
            "name": self.config.MILVUS_COLLECTION_NAME,
            "num_entities": collection.num_entities,
        }

        # Get index info
        indexes = collection.indexes
        if indexes:
            from pymilvus import Index
            index_info = collection.indexes[0]
            stats["index"] = {
                "field_name": index_info.field_name,
                "index_name": index_info.index_name,
            }

        return stats

    def __del__(self):
        """Cleanup connection on deletion."""
        # Note: Don't disconnect here as it may affect other instances
        pass
