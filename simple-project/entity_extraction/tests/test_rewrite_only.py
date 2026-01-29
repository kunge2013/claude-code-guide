#!/usr/bin/env python
"""Unit tests for question rewriting functionality - standalone version."""

import sys
from pathlib import Path

# Add src to path and import modules directly without going through package __init__
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import modules directly
import importlib.util

# Load time_normalizer
spec = importlib.util.spec_from_file_location(
    "time_normalizer",
    "src/langchain_entity_extraction/rewrite/time_normalizer.py"
)
time_normalizer = importlib.util.module_from_spec(spec)
sys.modules["time_normalizer"] = time_normalizer
spec.loader.exec_module(time_normalizer)

TimeNormalizer = time_normalizer.TimeNormalizer

# Load entity_mapper
spec = importlib.util.spec_from_file_location(
    "entity_mapper",
    "src/langchain_entity_extraction/rewrite/entity_mapper.py"
)
entity_mapper = importlib.util.module_from_spec(spec)
sys.modules["entity_mapper"] = entity_mapper

# Load logger utility first
spec = importlib.util.spec_from_file_location(
    "logger",
    "src/langchain_entity_extraction/utils/logger.py"
)
logger_module = importlib.util.module_from_spec(spec)
sys.modules["langchain_entity_extraction.utils.logger"] = logger_module
spec.loader.exec_module(logger_module)

# Now load entity_mapper
spec.loader.exec_module(entity_mapper)
EntityMapper = entity_mapper.EntityMapper

from datetime import date


def test_time_normalizer():
    """Test TimeNormalizer class."""
    print("\n=== Testing TimeNormalizer ===")

    normalizer = TimeNormalizer(date(2026, 1, 15))

    tests = [
        ("今年", "2026年"),
        ("去年", "2025年"),
        ("本月", "2026年1月"),
        ("上月", "2025年12月"),
        ("本季度", "2026年Q1"),
    ]

    for input_expr, expected in tests:
        result = normalizer.normalize(input_expr)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {input_expr:12} → {result:20} (expected: {expected})")

    print("\nAll TimeNormalizer tests passed!")


def test_entity_mapper():
    """Test EntityMapper class."""
    print("\n=== Testing EntityMapper ===")

    mapper = EntityMapper()

    # Test product mapping
    print("\nProduct mapping:")
    product_tests = [
        ("cdn", "cdn"),
        ("CDN", "cdn"),
        ("内容分发网络", "cdn"),
        ("ecs", "ecs"),
        ("云主机", "ecs"),
    ]

    for input_name, expected in product_tests:
        result = mapper.map_product_name(input_name)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {input_name:12} → {result:6} (expected: {expected})")

    # Test field mapping
    print("\nField mapping:")
    field_tests = [
        ("金额", "出账金额"),
        ("费用", "出账金额"),
        ("数量", "订单数量"),
        ("收入", "营业收入"),
    ]

    for input_name, expected in field_tests:
        result = mapper.map_field_name(input_name)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {input_name:6} → {result:8} (expected: {expected})")

    print("\nAll EntityMapper tests passed!")


def test_extract_from_text():
    """Test extraction from text."""
    print("\n=== Testing Extraction from Text ===")

    mapper = EntityMapper()

    # Test product extraction
    text1 = "cdn和ecs产品的金额是多少"
    products = mapper.extract_products_from_text(text1)
    print(f"\nText: {text1}")
    print(f"  Extracted products: {[p['standard_id'] for p in products]}")
    assert len(products) == 2
    assert products[0]["standard_id"] == "cdn"
    assert products[1]["standard_id"] == "ecs"

    # Test field extraction
    text2 = "查看金额和数量"
    fields = mapper.extract_fields_from_text(text2)
    print(f"\nText: {text2}")
    print(f"  Extracted fields: {[f['standard_name'] for f in fields]}")
    assert len(fields) == 2

    print("\nAll extraction tests passed!")


def test_formatting():
    """Test formatting for queries."""
    print("\n=== Testing Formatting ===")

    mapper = EntityMapper()

    formatted_product = mapper.format_product_for_query("cdn")
    print(f"  format_product_for_query('cdn') = {formatted_product}")
    assert formatted_product == "产品ID为cdn"

    formatted_time = mapper.format_time_for_query("2026年")
    print(f"  format_time_for_query('2026年') = {formatted_time}")
    assert formatted_time == "时间为2026年"

    print("\nAll formatting tests passed!")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Question Rewrite - Unit Tests")
    print("=" * 60)

    try:
        test_time_normalizer()
        test_entity_mapper()
        test_extract_from_text()
        test_formatting()

        print("\n" + "=" * 60)
        print("All tests passed successfully!")
        print("=" * 60 + "\n")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
