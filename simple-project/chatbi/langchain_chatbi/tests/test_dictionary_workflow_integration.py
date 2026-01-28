"""
Integration Tests for Dictionary Workflow

Tests the dictionary transformation in the full ChatBI workflow.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, MagicMock

from langchain_chatbi.graph.workflow import create_chatbi_graph
from langchain_chatbi.dictionary import get_dictionary_service


@pytest.fixture
def mock_db():
    """Create a mock database connection."""
    db = Mock()
    db.test_connection.return_value = True
    db.run.return_value = [
        {"prod_id": "1001", "prod_name": "云总机"},
        {"prod_id": "1002", "prod_name": "工作号"}
    ]
    db.get_all_schemas.return_value = [
        {
            "name": "special_settlement_rule_config",
            "columns": [
                {"name": "ID", "type": "bigint"},
                {"name": "PROD_ID", "type": "varchar"},
                {"name": "SETTLE_TYPE", "type": "varchar"}
            ]
        }
    ]
    db.disconnect = Mock()
    return db


@pytest.fixture
def temp_config_files():
    """Create temporary config files for testing."""
    temp_dir = tempfile.mkdtemp()

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
"""
    with open(dict_config_path, 'w', encoding='utf-8') as f:
        f.write(dict_config_content)

    synonym_config_path = os.path.join(temp_dir, "synonym_config.yaml")
    synonym_config_content = """
synonym_groups:
  - dictionary_name: product_dict
    canonical_value: "云总机"
    synonyms:
      - "云总机服务"
      - "云总机产品"
"""
    with open(synonym_config_path, 'w', encoding='utf-8') as f:
        f.write(synonym_config_content)

    yield dict_config_path, synonym_config_path

    import shutil
    shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_workflow_with_dictionary_transformation(temp_config_files, mock_db):
    """Test full workflow with dictionary transformation."""
    dict_config_path, synonym_config_path = temp_config_files

    # Initialize dictionary service
    dictionary_service = get_dictionary_service(
        config_path=dict_config_path,
        synonym_path=synonym_config_path,
        db_connection=None
    )
    await dictionary_service.initialize()

    # Create graph
    graph = create_chatbi_graph()

    # Config with dictionary service
    config = {
        "configurable": {
            "dictionary_service": dictionary_service,
            "db": mock_db
        }
    }

    # Initial state
    initial_state = {
        "question": "云总机有哪些配置",
        "session_id": "test-session",
        "language": "zh-CN",
        "messages": [],
        "sql_retry_count": 0,
        "should_stop": False,
        "table_schemas": mock_db.get_all_schemas()
    }

    # Execute workflow (just check preprocessing node)
    events = []
    async for event in graph.astream(initial_state, config=config):
        events.append(event)
        # Stop after preprocessing for this test
        if "preprocessing" in event:
            break

    # Verify preprocessing occurred
    preprocessing_output = None
    for event in events:
        if "preprocessing" in event:
            preprocessing_output = event["preprocessing"]
            break

    assert preprocessing_output is not None
    assert preprocessing_output.get("original_question") == "云总机有哪些配置"
    assert preprocessing_output.get("transformed_question") == "1001有哪些配置"
    assert "product_dict" in preprocessing_output.get("dictionary_transformations", {})


@pytest.mark.asyncio
async def test_workflow_without_dictionary_service(temp_config_files, mock_db):
    """Test workflow without dictionary service (fallback)."""
    # Create graph
    graph = create_chatbi_graph()

    # Config without dictionary service
    config = {
        "configurable": {
            "db": mock_db
        }
    }

    # Initial state
    initial_state = {
        "question": "云总机有哪些配置",
        "session_id": "test-session",
        "language": "zh-CN",
        "messages": [],
        "sql_retry_count": 0,
        "should_stop": False,
        "table_schemas": mock_db.get_all_schemas()
    }

    # Execute workflow
    events = []
    async for event in graph.astream(initial_state, config=config):
        events.append(event)
        if "preprocessing" in event:
            break

    # Verify preprocessing passes through unchanged
    preprocessing_output = None
    for event in events:
        if "preprocessing" in event:
            preprocessing_output = event["preprocessing"]
            break

    assert preprocessing_output is not None
    assert preprocessing_output.get("original_question") == "云总机有哪些配置"
    assert preprocessing_output.get("transformed_question") == "云总机有哪些配置"


@pytest.mark.asyncio
async def test_synonym_transformation_in_workflow(temp_config_files, mock_db):
    """Test synonym transformation in workflow."""
    dict_config_path, synonym_config_path = temp_config_files

    # Initialize dictionary service
    dictionary_service = get_dictionary_service(
        config_path=dict_config_path,
        synonym_path=synonym_config_path,
        db_connection=None
    )
    await dictionary_service.initialize()

    # Create graph
    graph = create_chatbi_graph()

    # Config with dictionary service
    config = {
        "configurable": {
            "dictionary_service": dictionary_service,
            "db": mock_db
        }
    }

    # Test with synonym
    initial_state = {
        "question": "云总机服务有哪些配置",
        "session_id": "test-session",
        "language": "zh-CN",
        "messages": [],
        "sql_retry_count": 0,
        "should_stop": False,
        "table_schemas": mock_db.get_all_schemas()
    }

    # Execute workflow
    events = []
    async for event in graph.astream(initial_state, config=config):
        events.append(event)
        if "preprocessing" in event:
            break

    # Verify synonym transformation
    preprocessing_output = None
    for event in events:
        if "preprocessing" in event:
            preprocessing_output = event["preprocessing"]
            break

    assert preprocessing_output is not None
    assert "1001" in preprocessing_output.get("transformed_question", "")
