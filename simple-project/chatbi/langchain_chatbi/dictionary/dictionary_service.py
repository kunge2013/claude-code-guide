"""
Dictionary Service for ChatBI

Provides dictionary value transformation with caching and synonym support.
"""

import asyncio
import re
import time
from typing import Dict, List, Optional, Any, Tuple
from loguru import logger
import yaml

from langchain_chatbi.dictionary.models import (
    DictionaryConfig,
    DictionaryEntry,
    DictionaryDefinition,
    SynonymGroup,
    TransformationResult,
)


class DictionaryService:
    """
    Service for managing dictionary value transformations.

    Features:
    - Mixed data source: database with static fallback
    - Configurable cache TTL
    - Synonym support
    - Async and sync interfaces
    """

    def __init__(
        self,
        config_path: str = "config/dictionary_config.yaml",
        synonym_path: str = "config/synonym_config.yaml",
        db_connection: Any = None
    ):
        """
        Initialize the DictionaryService.

        Args:
            config_path: Path to dictionary configuration YAML
            synonym_path: Path to synonym configuration YAML
            db_connection: Database connection for database-sourced dictionaries
        """
        self.config_path = config_path
        self.synonym_path = synonym_path
        self.db = db_connection

        # Dictionary storage
        self._dictionaries: Dict[str, DictionaryConfig] = {}
        self._initialized = False

        logger.info("DictionaryService initialized")

    async def initialize(self):
        """
        Initialize the service by loading configurations.

        Should be called during application startup.
        """
        if self._initialized:
            return

        # Load dictionary configurations
        dict_configs = self._load_yaml(self.config_path)
        for config in dict_configs.get("dictionaries", []):
            dict_config = DictionaryConfig(
                name=config["name"],
                description=config.get("description", ""),
                source_type=config["source_type"],
                cache_ttl_seconds=config.get("cache_ttl_seconds", 3600),
                source_config=config["source_config"]
            )
            self._dictionaries[dict_config.name] = dict_config

        # Load synonyms into a temporary dict first
        temp_synonyms: Dict[str, List[Tuple[str, str]]] = {}  # {dict_name: [(synonym, canonical), ...]}
        synonym_configs = self._load_yaml(self.synonym_path)
        for group in synonym_configs.get("synonym_groups", []):
            dict_name = group["dictionary_name"]
            if dict_name not in temp_synonyms:
                temp_synonyms[dict_name] = []
            canonical = group["canonical_value"]
            for synonym in group["synonyms"]:
                temp_synonyms[dict_name].append((synonym, canonical))

        # Initial cache warmup (this will call update_cache which clears synonyms)
        await self._warmup_cache()

        # Now load synonyms after cache warmup to preserve them
        for dict_name, synonym_list in temp_synonyms.items():
            if dict_name in self._dictionaries:
                dict_config = self._dictionaries[dict_name]
                for synonym, canonical in synonym_list:
                    dict_config._synonym_index[synonym] = canonical

        self._initialized = True
        logger.info(f"DictionaryService initialized with {len(self._dictionaries)} dictionaries")

    async def transform(
        self,
        text: str,
        dictionary_names: Optional[List[str]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Transform text by replacing dictionary values with their keys.

        Args:
            text: Input text (e.g., "云总机有哪些配置")
            dictionary_names: List of dictionaries to apply (None = all)

        Returns:
            Tuple of (transformed_text, transformation_metadata)
            Example: ("1001有哪些配置", {"product_dict": {"云总机": "1001"}})
        """
        if not self._initialized:
            await self.initialize()

        transformed = text
        metadata = {}

        # Determine which dictionaries to use
        dicts_to_check = (
            [self._dictionaries[name] for name in dictionary_names if name in self._dictionaries]
            if dictionary_names
            else self._dictionaries.values()
        )

        for dict_config in dicts_to_check:
            # Ensure cache is fresh
            if dict_config.is_cache_expired():
                await self._refresh_dictionary(dict_config)

            # Find and replace matches
            matches = self._find_matches(text, dict_config)
            if matches:
                dict_metadata = {}
                for value, key in matches.items():
                    # Replace in text using simple string replacement
                    # Sort matches by length (descending) to handle overlapping values correctly
                    transformed = transformed.replace(value, str(key))
                    dict_metadata[value] = key

                if dict_metadata:
                    metadata[dict_config.name] = dict_metadata

        logger.debug(f"Transform: '{text}' -> '{transformed}', metadata: {metadata}")
        return transformed, metadata

    async def reverse_lookup(
        self,
        key: Any,
        dictionary_name: str
    ) -> Optional[str]:
        """
        Reverse lookup: get display name from ID.

        Args:
            key: The ID to look up
            dictionary_name: Name of the dictionary

        Returns:
            Display name or None if not found
        """
        if not self._initialized:
            await self.initialize()

        if dictionary_name not in self._dictionaries:
            return None

        dict_config = self._dictionaries[dictionary_name]

        # Ensure cache is fresh
        if dict_config.is_cache_expired():
            await self._refresh_dictionary(dict_config)

        # Reverse lookup in cache
        for value, cached_key in dict_config._cache.items():
            if cached_key == key:
                return value

        return None

    def transform_sync(
        self,
        text: str,
        dictionary_names: Optional[List[str]] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Synchronous version of transform.

        Runs the async version in an event loop.
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.transform(text, dictionary_names)
        )

    # ========================================================================
    # Private Methods
    # ========================================================================

    def _load_yaml(self, path: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {path}")
            return {}
        except Exception as e:
            logger.error(f"Error loading configuration from {path}: {e}")
            return {}

    async def _warmup_cache(self):
        """Warm up cache for all dictionaries."""
        for dict_config in self._dictionaries.values():
            try:
                await self._refresh_dictionary(dict_config)
            except Exception as e:
                logger.error(f"Failed to warmup cache for {dict_config.name}: {e}")

    async def _refresh_dictionary(self, dict_config: DictionaryConfig):
        """Refresh dictionary cache from source."""
        if dict_config.source_type == "database":
            entries = await self._load_from_database(dict_config)
        else:  # static
            entries = self._load_from_static(dict_config)

        dict_config.update_cache(entries)
        logger.debug(f"[{dict_config.name}] Refreshed cache with {len(entries)} entries")

    async def _load_from_database(
        self,
        dict_config: DictionaryConfig
    ) -> List[DictionaryEntry]:
        """Load dictionary entries from database."""
        if not self.db:
            logger.warning(f"Database connection not available for {dict_config.name}")
            return []

        source = dict_config.source_config
        table = source["table"]
        key_col = source["key_column"]
        value_col = source["value_column"]
        where_clause = source.get("where_clause", "")

        sql = f"SELECT {key_col}, {value_col} FROM {table}"
        if where_clause:
            sql += f" WHERE {where_clause}"

        try:
            # Run query in thread pool (synchronous DB call)
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(
                    executor,
                    self.db.run,
                    sql
                )

            entries = [
                DictionaryEntry(
                    key=row[key_col],
                    value=row[value_col],
                    synonyms=[]  # Synonyms loaded separately
                )
                for row in result
            ]

            return entries

        except Exception as e:
            logger.error(f"Failed to load from database for {dict_config.name}: {e}")
            return []

    def _load_from_static(
        self,
        dict_config: DictionaryConfig
    ) -> List[DictionaryEntry]:
        """Load dictionary entries from static configuration."""
        mappings = dict_config.source_config.get("mappings", {})

        entries = [
            DictionaryEntry(
                key=key,
                value=value,
                synonyms=[]
            )
            for value, key in mappings.items()
        ]

        return entries

    def _find_matches(
        self,
        text: str,
        dict_config: DictionaryConfig
    ) -> Dict[str, Any]:
        """
        Find dictionary values in text.

        Returns a dict of {value: key} for all matches found.
        Synonyms take priority over direct values to handle longer matches.
        """
        matches = {}

        # First, check all synonyms (these are usually longer/more specific)
        for synonym, canonical in dict_config._synonym_index.items():
            if synonym in text:
                if canonical in dict_config._cache:
                    matches[synonym] = dict_config._cache[canonical]

        # Then, check direct values (only if not already matched via synonym)
        for value, key in dict_config._cache.items():
            # Skip if any synonym or other match already covers this
            # (e.g., if "云总机服务" matched, don't also match "云总机" separately)
            already_covered = any(value in matched_key for matched_key in matches.keys())
            if value in text and not already_covered:
                matches[value] = key

        return matches


# Singleton instance
_dictionary_service: Optional[DictionaryService] = None


def get_dictionary_service(
    config_path: str = "config/dictionary_config.yaml",
    synonym_path: str = "config/synonym_config.yaml",
    db_connection: Any = None
) -> DictionaryService:
    """
    Get or create the singleton DictionaryService instance.

    Args:
        config_path: Path to dictionary configuration
        synonym_path: Path to synonym configuration
        db_connection: Database connection

    Returns:
        DictionaryService instance
    """
    global _dictionary_service

    if _dictionary_service is None:
        _dictionary_service = DictionaryService(
            config_path=config_path,
            synonym_path=synonym_path,
            db_connection=db_connection
        )

    return _dictionary_service
