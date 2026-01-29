#!/usr/bin/env python
"""Standalone unit tests for question rewriting - TimeNormalizer and EntityMapper only."""

import sys
from datetime import date


class TestTimeNormalizer:
    """Tests for TimeNormalizer class."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def test_normalize_this_year(self):
        """Test normalizing '今年' to current year."""
        # Import and create TimeNormalizer
        from src.langchain_entity_extraction.rewrite.time_normalizer import TimeNormalizer
        normalizer = TimeNormalizer(date(2026, 1, 15))
        result = normalizer.normalize("今年")
        assert result == "2026年", f"Expected '2026年', got '{result}'"
        self._pass("今年 → 2026年")

    def test_normalize_last_year(self):
        """Test normalizing '去年' to last year."""
        from src.langchain_entity_extraction.rewrite.time_normalizer import TimeNormalizer
        normalizer = TimeNormalizer(date(2026, 1, 15))
        result = normalizer.normalize("去年")
        assert result == "2025年", f"Expected '2025年', got '{result}'"
        self._pass("去年 → 2025年")

    def test_normalize_this_month(self):
        """Test normalizing '本月' to current month."""
        from src.langchain_entity_extraction.rewrite.time_normalizer import TimeNormalizer
        normalizer = TimeNormalizer(date(2026, 1, 15))
        result = normalizer.normalize("本月")
        assert result == "2026年1月", f"Expected '2026年1月', got '{result}'"
        self._pass("本月 → 2026年1月")

    def test_normalize_last_month(self):
        """Test normalizing '上月' to last month."""
        from src.langchain_entity_extraction.rewrite.time_normalizer import TimeNormalizer
        normalizer = TimeNormalizer(date(2026, 1, 15))
        result = normalizer.normalize("上月")
        assert result == "2025年12月", f"Expected '2025年12月', got '{result}'"
        self._pass("上月 → 2025年12月")

    def test_normalize_this_quarter(self):
        """Test normalizing '本季度' to current quarter."""
        from src.langchain_entity_extraction.rewrite.time_normalizer import TimeNormalizer
        normalizer = TimeNormalizer(date(2026, 1, 15))
        result = normalizer.normalize("本季度")
        assert result == "2026年Q1", f"Expected '2026年Q1', got '{result}'"
        self._pass("本季度 → 2026年Q1")

    def test_extract_time_from_text(self):
        """Test extracting time expression from text."""
        from src.langchain_entity_extraction.rewrite.time_normalizer import TimeNormalizer
        normalizer = TimeNormalizer(date(2026, 1, 15))
        result = normalizer.extract_time_from_text("今年cdn产品金额")

        assert result["found"] is True, "Expected found=True"
        assert result["original"] == "今年", f"Expected original='今年', got '{result['original']}'"
        assert result["normalized"] == "2026年", f"Expected normalized='2026年', got '{result['normalized']}'"
        self._pass("extract_time_from_text: 今年cdn产品金额")

    def _pass(self, test_name):
        """Record a passed test."""
        self.passed += 1
        print(f"  ✓ {test_name}")

    def _fail(self, test_name, error):
        """Record a failed test."""
        self.failed += 1
        print(f"  ✗ {test_name}: {error}")


class TestEntityMapper:
    """Tests for EntityMapper class."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def test_map_product_name_lowercase(self):
        """Test mapping lowercase product name."""
        from src.langchain_entity_extraction.rewrite.entity_mapper import EntityMapper
        mapper = EntityMapper()
        result = mapper.map_product_name("cdn")
        assert result == "cdn", f"Expected 'cdn', got '{result}'"
        self._pass("map_product_name: cdn → cdn")

    def test_map_product_name_uppercase(self):
        """Test mapping uppercase product name."""
        from src.langchain_entity_extraction.rewrite.entity_mapper import EntityMapper
        mapper = EntityMapper()
        result = mapper.map_product_name("CDN")
        assert result == "cdn", f"Expected 'cdn', got '{result}'"
        self._pass("map_product_name: CDN → cdn")

    def test_map_product_name_alias(self):
        """Test mapping product alias."""
        from src.langchain_entity_extraction.rewrite.entity_mapper import EntityMapper
        mapper = EntityMapper()
        result = mapper.map_product_name("内容分发网络")
        assert result == "cdn", f"Expected 'cdn', got '{result}'"
        self._pass("map_product_name: 内容分发网络 → cdn")

    def test_map_field_name_amount(self):
        """Test mapping field name variations to '出账金额'."""
        from src.langchain_entity_extraction.rewrite.entity_mapper import EntityMapper
        mapper = EntityMapper()

        result = mapper.map_field_name("金额")
        assert result == "出账金额", f"Expected '出账金额', got '{result}'"
        self._pass("map_field_name: 金额 → 出账金额")

        result = mapper.map_field_name("费用")
        assert result == "出账金额", f"Expected '出账金额', got '{result}'"
        self._pass("map_field_name: 费用 → 出账金额")

    def test_extract_products_from_text(self):
        """Test extracting products from text."""
        from src.langchain_entity_extraction.rewrite.entity_mapper import EntityMapper
        mapper = EntityMapper()
        result = mapper.extract_products_from_text("cdn和ecs产品的金额")

        assert len(result) == 2, f"Expected 2 products, got {len(result)}"
        assert result[0]["standard_id"] == "cdn", f"Expected first product to be 'cdn'"
        assert result[1]["standard_id"] == "ecs", f"Expected second product to be 'ecs'"
        self._pass("extract_products_from_text: cdn和ecs产品")

    def test_format_product_for_query(self):
        """Test formatting product for query."""
        from src.langchain_entity_extraction.rewrite.entity_mapper import EntityMapper
        mapper = EntityMapper()
        result = mapper.format_product_for_query("cdn")
        assert result == "产品ID为cdn", f"Expected '产品ID为cdn', got '{result}'"
        self._pass("format_product_for_query: cdn → 产品ID为cdn")

    def _pass(self, test_name):
        """Record a passed test."""
        self.passed += 1
        print(f"  ✓ {test_name}")

    def _fail(self, test_name, error):
        """Record a failed test."""
        self.failed += 1
        print(f"  ✗ {test_name}: {error}")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Question Rewrite - Standalone Unit Tests")
    print("=" * 60)

    total_passed = 0
    total_failed = 0

    # Test TimeNormalizer
    print("\n=== Testing TimeNormalizer ===")
    time_tests = TestTimeNormalizer()

    tests = [
        time_tests.test_normalize_this_year,
        time_tests.test_normalize_last_year,
        time_tests.test_normalize_this_month,
        time_tests.test_normalize_last_month,
        time_tests.test_normalize_this_quarter,
        time_tests.test_extract_time_from_text,
    ]

    for test in tests:
        try:
            test()
        except AssertionError as e:
            time_tests._fail(test.__name__, str(e))
        except Exception as e:
            time_tests._fail(test.__name__, str(e))

    total_passed += time_tests.passed
    total_failed += time_tests.failed

    # Test EntityMapper
    print("\n=== Testing EntityMapper ===")
    entity_tests = TestEntityMapper()

    tests = [
        entity_tests.test_map_product_name_lowercase,
        entity_tests.test_map_product_name_uppercase,
        entity_tests.test_map_product_name_alias,
        entity_tests.test_map_field_name_amount,
        entity_tests.test_extract_products_from_text,
        entity_tests.test_format_product_for_query,
    ]

    for test in tests:
        try:
            test()
        except AssertionError as e:
            entity_tests._fail(test.__name__, str(e))
        except Exception as e:
            entity_tests._fail(test.__name__, str(e))

    total_passed += entity_tests.passed
    total_failed += entity_tests.failed

    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {total_passed} passed, {total_failed} failed")
    print("=" * 60)

    if total_failed > 0:
        print("\n✗ Some tests failed")
        sys.exit(1)
    else:
        print("\n✓ All tests passed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
