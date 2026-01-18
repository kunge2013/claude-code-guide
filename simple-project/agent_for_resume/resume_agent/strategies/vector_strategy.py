"""
Vector search strategy using Milvus.

This strategy implements semantic vector search using Milvus database
and FlagEmbedding for text-to-vector conversion.
"""
import pandas as pd
from typing import Optional

from .base import SearchStrategy, SearchResult, MatchResult
from ..repositories import MilvusRepository
from ..embeddings import FlagEmbeddingService


class VectorSearchStrategy(SearchStrategy):
    """
    Vector-based semantic search strategy.

    Uses Milvus vector database and FlagEmbedding to find templates
    based on semantic similarity rather than exact string matching.
    """

    def __init__(self, config):
        """
        Initialize vector search strategy.

        Args:
            config: Config object with Milvus and embedding settings
        """
        self.config = config
        self._repository: Optional[MilvusRepository] = None
        self._embedding_service: Optional[FlagEmbeddingService] = None
        self._knowledge_base: Optional[pd.DataFrame] = None

    @property
    def repository(self) -> MilvusRepository:
        """Lazy load Milvus repository."""
        if self._repository is None:
            self._repository = MilvusRepository(self.config)
        return self._repository

    @property
    def embedding_service(self) -> FlagEmbeddingService:
        """Lazy load embedding service."""
        if self._embedding_service is None:
            self._embedding_service = FlagEmbeddingService(
                model_name=self.config.EMBEDDING_MODEL_NAME,
                device=self.config.EMBEDDING_DEVICE,
                cache_dir=self.config.EMBEDDING_CACHE_DIR,
                enable_cache=self.config.ENABLE_EMBEDDING_CACHE
            )
        return self._embedding_service

    def _load_knowledge_base(self) -> pd.DataFrame:
        """Load the Excel knowledge base file."""
        if self._knowledge_base is not None:
            return self._knowledge_base

        self._knowledge_base = pd.read_excel(self.config.EXCEL_FILE_PATH)
        return self._knowledge_base

    def search(self, query: str) -> SearchResult:
        """
        Search for templates using vector similarity.

        Args:
            query: Search query string

        Returns:
            SearchResult with matched templates
        """
        # Convert query to embedding vector
        query_vector = self.embedding_service.encode_query(query)

        # Perform vector search
        results = self.repository.search(
            query_vector=query_vector,
            top_k=self.config.VECTOR_TOP_K
        )

        # Convert to MatchResult objects
        matches = []
        for result in results:
            # Filter by threshold
            score = result["score"]
            if score >= self.config.VECTOR_THRESHOLD:
                matches.append(MatchResult(
                    template_name=result["template_name"],
                    download_link=result["download_link"],
                    score=score,
                    match_type="vector"
                ))

        # If no matches found, return all available templates as suggestions
        if not matches:
            df = self._load_knowledge_base()
            for template in df['问题'].tolist():
                matches.append(MatchResult(
                    template_name=template,
                    download_link="",
                    score=0.0,
                    match_type="suggestion"
                ))

        return SearchResult(
            strategy_type="vector",
            matches=matches,
            query=query
        )

    def get_strategy_name(self) -> str:
        """Get the strategy name."""
        return "vector"
