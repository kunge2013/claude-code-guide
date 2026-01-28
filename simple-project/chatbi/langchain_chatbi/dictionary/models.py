"""
Dictionary Data Models

Pydantic models for dictionary configuration and entries.
"""

from typing import Dict, List, Any, Optional, Literal, Union
from pydantic import BaseModel, Field
from dataclasses import dataclass
from time import time


@dataclass
class DictionaryEntry:
    """A single dictionary entry."""
    key: Any  # The ID value (e.g., 1001)
    value: str  # The display name (e.g., "云总机")
    synonyms: List[str]  # Alternative names


@dataclass
class DictionaryConfig:
    """Configuration for a single dictionary."""
    name: str
    description: str
    source_type: str  # 'database' or 'static'
    cache_ttl_seconds: int
    source_config: Dict[str, Any]

    # Runtime state
    _cache: Dict[str, Any] = None
    _cache_time: float = 0
    _synonym_index: Dict[str, str] = None  # synonym -> canonical value

    def __post_init__(self):
        if self._cache is None:
            self._cache = {}
        if self._synonym_index is None:
            self._synonym_index = {}

    def is_cache_expired(self) -> bool:
        """Check if cache has expired."""
        return time() - self._cache_time > self.cache_ttl_seconds

    def update_cache(self, entries: List[DictionaryEntry]):
        """Update the cache with new entries."""
        self._cache.clear()
        self._synonym_index.clear()

        for entry in entries:
            # Index by canonical value
            self._cache[entry.value] = entry.key

            # Index by synonyms
            for synonym in entry.synonyms:
                self._synonym_index[synonym] = entry.value

        self._cache_time = time()


class DatabaseSourceConfig(BaseModel):
    """Database source configuration."""
    type: Literal["database"] = "database"
    table: str = Field(..., description="Source table name")
    key_column: str = Field(..., description="Column containing the ID value")
    value_column: str = Field(..., description="Column containing the display name")
    where_clause: Optional[str] = Field(None, description="Optional WHERE clause")


class StaticSourceConfig(BaseModel):
    """Static source configuration."""
    type: Literal["static"] = "static"
    mappings: Dict[str, Any] = Field(default_factory=dict, description="Static name to ID mappings")


# Union type for source config
DictionarySourceConfig = Union[DatabaseSourceConfig, StaticSourceConfig]


class DictionaryDefinition(BaseModel):
    """Definition of a single dictionary."""
    name: str = Field(..., description="Unique identifier for this dictionary")
    description: str = Field(default="", description="Human-readable description")
    source_type: Literal["database", "static"] = Field(..., description="Source type: 'database' or 'static'")
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")
    source_config: Dict[str, Any] = Field(..., description="Source configuration")


class DictionaryConfigFile(BaseModel):
    """Root model for dictionary configuration file."""
    dictionaries: List[DictionaryDefinition] = Field(default_factory=list)


class SynonymGroup(BaseModel):
    """A group of synonyms mapping to a canonical value."""
    dictionary_name: str = Field(..., description="Which dictionary this applies to")
    canonical_value: str = Field(..., description="The canonical name that maps to the ID")
    synonyms: List[str] = Field(..., description="Alternative names that should map to the same ID")


class SynonymConfigFile(BaseModel):
    """Root model for synonym configuration file."""
    synonym_groups: List[SynonymGroup] = Field(default_factory=list)


class TransformationMetadata(BaseModel):
    """Metadata about a transformation."""
    dictionary_name: str
    transformations: Dict[str, Any] = Field(default_factory=dict, description="original_value -> transformed_value")


class TransformationResult(BaseModel):
    """Result of a text transformation."""
    original_text: str
    transformed_text: str
    metadata: Dict[str, TransformationMetadata] = Field(default_factory=dict)
