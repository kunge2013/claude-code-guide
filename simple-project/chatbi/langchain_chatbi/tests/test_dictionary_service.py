"""
Unit Tests for Dictionary Service

Tests the dictionary value transformation functionality.
"""

import pytest
import asyncio
import tempfile
import os
from typing import Dict, Any

from langchain_chatbi.dictionary.dictionary_service import DictionaryService
from langchain_chatbi.dictionary.models import DictionaryEntry


@pytest.fixture
def temp_config_files():
    """Create temporary config files for testing."""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()

    # Create dictionary config
    dict_config_path = os.path.join(temp_dir, "dictionary_config.yaml")
    dict_config_content = """
dictionaries:
  - name: product_dict
    description: "Product name to ID mapping"
    source_type: static
    cache_ttl_seconds: 3600
    source_config:
      type: static
      mappings:
        "云总机": "1001"
        "工作号": "1002"

  - name: status_dict
    description: "Status name to code mapping"
    source_type: static
    cache_ttl_seconds: 7200
    source_config:
      type: static
      mappings:
        "启用": "1000"
        "禁用": "1001"
"""
    with open(dict_config_path, 'w', encoding='utf-8') as f:
        f.write(dict_config_content)

    # Create synonym config
    synonym_config_path = os.path.join(temp_dir, "synonym_config.yaml")
    synonym_config_content = """
synonym_groups:
  - dictionary_name: product_dict
    canonical_value: "云总机"
    synonyms:
      - "云总机服务"
      - "云总机产品"
      - "企业云总机"

  - dictionary_name: product_dict
    canonical_value: "工作号"
    synonyms:
      - "工作号服务"
      - "企业工作号"
"""
    with open(synonym_config_path, 'w', encoding='utf-8') as f:
        f.write(synonym_config_content)

    yield dict_config_path, synonym_config_path

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_dictionary_initialization(temp_config_files):
    """Test dictionary service initialization."""
    dict_config_path, synonym_config_path = temp_config_files

    service = DictionaryService(
        config_path=dict_config_path,
        synonym_path=synonym_config_path,
        db_connection=None
    )

    await service.initialize()

    assert service._initialized is True
    assert len(service._dictionaries) == 2
    assert "product_dict" in service._dictionaries
    assert "status_dict" in service._dictionaries


@pytest.mark.asyncio
async def test_basic_transformation(temp_config_files):
    """Test basic value to ID transformation."""
    dict_config_path, synonym_config_path = temp_config_files

    service = DictionaryService(
        config_path=dict_config_path,
        synonym_path=synonym_config_path,
        db_connection=None
    )
    await service.initialize()

    # Test basic transformation
    transformed, metadata = await service.transform("云总机有哪些配置")
    assert transformed == "1001有哪些配置"
    assert "product_dict" in metadata
    assert metadata["product_dict"]["云总机"] == "1001"


@pytest.mark.asyncio
async def test_synonym_transformation(temp_config_files):
    """Test synonym transformation."""
    dict_config_path, synonym_config_path = temp_config_files

    service = DictionaryService(
        config_path=dict_config_path,
        synonym_path=synonym_config_path,
        db_connection=None
    )
    await service.initialize()

    # Test synonym transformation
    transformed, metadata = await service.transform("云总机服务有哪些配置")
    assert transformed == "1001有哪些配置"
    assert "product_dict" in metadata

    # Test another synonym
    transformed, metadata = await service.transform("企业云总机有哪些配置")
    assert transformed == "1001有哪些配置"


@pytest.mark.asyncio
async def test_multiple_transformation(temp_config_files):
    """Test multiple values in one text."""
    dict_config_path, synonym_config_path = temp_config_files

    service = DictionaryService(
        config_path=dict_config_path,
        synonym_path=synonym_config_path,
        db_connection=None
    )
    await service.initialize()

    # Test multiple transformations
    transformed, metadata = await service.transform("云总机和工作号的配置")
    assert "1001" in transformed
    assert "1002" in transformed
    assert "product_dict" in metadata


@pytest.mark.asyncio
async def test_no_match(temp_config_files):
    """Test behavior when no match is found."""
    dict_config_path, synonym_config_path = temp_config_files

    service = DictionaryService(
        config_path=dict_config_path,
        synonym_path=synonym_config_path,
        db_connection=None
    )
    await service.initialize()

    # Test with unknown product
    transformed, metadata = await service.transform("未知产品有哪些配置")
    assert transformed == "未知产品有哪些配置"
    assert metadata == {}


@pytest.mark.asyncio
async def test_specific_dictionary(temp_config_files):
    """Test using specific dictionaries only."""
    dict_config_path, synonym_config_path = temp_config_files

    service = DictionaryService(
        config_path=dict_config_path,
        synonym_path=synonym_config_path,
        db_connection=None
    )
    await service.initialize()

    # Test with only status_dict
    transformed, metadata = await service.transform(
        "启用的配置",
        dictionary_names=["status_dict"]
    )
    assert "1000" in transformed
    assert "status_dict" in metadata
    assert "product_dict" not in metadata


@pytest.mark.asyncio
async def test_reverse_lookup(temp_config_files):
    """Test reverse lookup (ID to name)."""
    dict_config_path, synonym_config_path = temp_config_files

    service = DictionaryService(
        config_path=dict_config_path,
        synonym_path=synonym_config_path,
        db_connection=None
    )
    await service.initialize()

    # Test reverse lookup
    name = await service.reverse_lookup("1001", "product_dict")
    assert name == "云总机"

    # Test with non-existent ID
    name = await service.reverse_lookup("9999", "product_dict")
    assert name is None


@pytest.mark.asyncio
async def test_cache_expiration(temp_config_files):
    """Test cache expiration logic."""
    dict_config_path, synonym_config_path = temp_config_files

    # Create service with very short TTL
    service = DictionaryService(
        config_path=dict_config_path,
        synonym_path=synonym_config_path,
        db_connection=None
    )

    # Manually create a dict config with short TTL
    from langchain_chatbi.dictionary.models import DictionaryConfig
    test_config = DictionaryConfig(
        name="test_dict",
        description="Test",
        source_type="static",
        cache_ttl_seconds=1,  # 1 second TTL
        source_config={"type": "static", "mappings": {"a": "1"}}
    )

    # Fresh cache
    test_config.update_cache([])
    assert test_config.is_cache_expired() is False

    # Wait for expiration
    import time
    time.sleep(2)
    assert test_config.is_cache_expired() is True


def test_sync_transform(temp_config_files):
    """Test synchronous version of transform."""
    dict_config_path, synonym_config_path = temp_config_files

    service = DictionaryService(
        config_path=dict_config_path,
        synonym_path=synonym_config_path,
        db_connection=None
    )

    # Use sync version (will run async in event loop)
    transformed, metadata = service.transform_sync("云总机有哪些配置")
    assert "1001" in transformed
    assert "product_dict" in metadata
