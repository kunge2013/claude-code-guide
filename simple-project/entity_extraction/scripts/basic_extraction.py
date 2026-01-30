#!/usr/bin/env python3
"""
Basic Entity Extraction Examples

This script demonstrates basic entity extraction using LangChain.
Based on the official documentation:
https://python.langchain.com.cn/docs/modules/chains/additional/extraction

Examples include:
1. Person extraction using Pydantic models
2. Person extraction using schema dictionaries
3. Organization extraction
4. Product extraction
"""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_entity_extraction import ExtractionService
from langchain_entity_extraction.models.entity_schemas import (
    PersonEntity,
    OrganizationEntity,
    ProductEntity,
)
from langchain_entity_extraction.utils.logger import setup_logger

# Setup logger
setup_logger()


async def example_1_person_extraction_pydantic():
    """
    Example 1: Extract person information using Pydantic models.

    This is the RECOMMENDED approach for production use.
    It provides type safety and automatic validation.
    """
    print("\n" + "=" * 60)
    print("Example 1: Person Extraction (Pydantic)")
    print("=" * 60)

    text = """
    John Smith is a 35-year-old software engineer at Google.
    He specializes in Python and machine learning.
    You can reach him at john.smith@example.com or 555-1234.
    """

    print(f"\nInput text:\n{text}")

    service = ExtractionService()
    persons = await service.extract_persons(text)

    print(f"\nExtracted {len(persons)} person(s):")
    for person in persons:
        print(f"\n  Name: {person.name}")
        print(f"  Age: {person.age}")
        print(f"  Title: {person.title}")
        print(f"  Organization: {person.organization}")
        print(f"  Email: {person.email}")
        print(f"  Phone: {person.phone}")
        print(f"  Skills: {', '.join(person.skills) if person.skills else 'N/A'}")


async def example_2_person_extraction_schema():
    """
    Example 2: Extract person information using schema dictionaries.

    This is a more flexible approach that works with various LLM providers.
    However, it lacks type safety compared to Pydantic models.
    """
    print("\n" + "=" * 60)
    print("Example 2: Person Extraction (Schema Dictionary)")
    print("=" * 60)

    text = """
    Alex is 5 feet tall. Claudia is 1 feet taller than Alex and jumps higher than him.
    Claudia is a brunette and Alex is blonde.
    Alex's dog Frosty is a labrador and likes to play hide and seek.
    """

    print(f"\nInput text:\n{text}")

    # Define schema (from official documentation example)
    schema = {
        "properties": {
            "person_name": {"type": "string"},
            "person_height": {"type": "integer"},
            "person_hair_color": {"type": "string"},
            "dog_name": {"type": "string"},
            "dog_breed": {"type": "string"},
        },
        "required": ["person_name", "person_height"],
    }

    print("\nSchema:")
    print(f"  Properties: {list(schema['properties'].keys())}")
    print(f"  Required: {schema['required']}")

    service = ExtractionService()
    persons = await service.extract_persons(text, use_schema=True)

    # Note: When using schema extraction, the returned entities are dictionaries
    # We can convert them to PersonEntity if needed
    print(f"\nExtracted {len(persons)} person(s):")
    for i, person in enumerate(persons, 1):
        # Schema extraction returns dictionaries
        if isinstance(person, dict):
            print(f"\n  Person {i}:")
            for key, value in person.items():
                print(f"    {key}: {value}")
        else:
            print(f"\n  Person {i}: {person}")


async def example_3_organization_extraction():
    """Example 3: Extract organization information."""
    print("\n" + "=" * 60)
    print("Example 3: Organization Extraction")
    print("=" * 60)

    text = """
    Google was founded in 1998 by Larry Page and Sergey Brin.
    The company is headquartered in Mountain View, California
    and operates in the technology industry. Visit them at https://www.google.com
    """

    print(f"\nInput text:\n{text}")

    service = ExtractionService()
    organizations = await service.extract_organizations(text)

    print(f"\nExtracted {len(organizations)} organization(s):")
    for org in organizations:
        print(f"\n  Name: {org.name}")
        print(f"  Industry: {org.industry}")
        print(f"  Founded Year: {org.founded_year}")
        print(f"  Headquarters: {org.headquarters}")
        print(f"  Website: {org.website}")


async def example_4_product_extraction():
    """Example 4: Extract product information."""
    print("\n" + "=" * 60)
    print("Example 4: Product Extraction")
    print("=" * 60)

    text = """
    The iPhone 15 Pro is Apple's latest flagship smartphone.
    It features a titanium design, A17 Pro chip, and 5G connectivity.
    Priced at $999.99, it's available in various storage configurations.
    """

    print(f"\nInput text:\n{text}")

    service = ExtractionService()
    products = await service.extract_products(text)

    print(f"\nExtracted {len(products)} product(s):")
    for product in products:
        print(f"\n  Name: {product.name}")
        print(f"  Price: ${product.price} {product.currency}")
        print(f"  Category: {product.category}")
        print(f"  Features: {', '.join(product.features) if product.features else 'N/A'}")
        print(f"  Manufacturer: {product.manufacturer}")


async def example_5_extract_all():
    """Example 5: Extract all entity types at once."""
    print("\n" + "=" * 60)
    print("Example 5: Extract All Entity Types")
    print("=" * 60)

    text = """
    John Smith is a software engineer at Google's Mountain View office.
    He's working on a new product called Pixel 8 Pro which costs $999.
    The product launch event is scheduled for October 2023 in New York.
    """

    print(f"\nInput text:\n{text}")

    service = ExtractionService()
    entities = await service.extract_all(text)

    print("\nExtracted entities:")

    if entities["persons"]:
        print(f"\n  Persons ({len(entities['persons'])}):")
        for person in entities["persons"]:
            print(f"    - {person.name} ({person.title})")

    if entities["organizations"]:
        print(f"\n  Organizations ({len(entities['organizations'])}):")
        for org in entities["organizations"]:
            print(f"    - {org.name}")

    if entities["products"]:
        print(f"\n  Products ({len(entities['products'])}):")
        for product in entities["products"]:
            print(f"    - {product.name} (${product.price})")

    if entities["locations"]:
        print(f"\n  Locations ({len(entities['locations'])}):")
        for location in entities["locations"]:
            print(f"    - {location.name}")

    if entities["events"]:
        print(f"\n  Events ({len(entities['events'])}):")
        for event in entities["events"]:
            print(f"    - {event.name}")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("LangChain Entity Extraction - Basic Examples")
    print("=" * 60)

    try:
        await example_1_person_extraction_pydantic()
        await example_2_person_extraction_schema()
        await example_3_organization_extraction()
        await example_4_product_extraction()
        await example_5_extract_all()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
