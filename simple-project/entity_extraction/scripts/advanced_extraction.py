#!/usr/bin/env python3
"""
Advanced Entity Extraction Examples

This script demonstrates advanced entity extraction features including:
1. Custom schema extraction
2. Relationship extraction
3. Batch processing
4. Error handling
5. Both synchronous and asynchronous APIs
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List

from pydantic import BaseModel, Field

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_entity_extraction import ExtractionService
from langchain_entity_extraction.models.entity_schemas import EntityRelationship
from langchain_entity_extraction.utils.logger import setup_logger

# Setup logger
setup_logger()


# Custom schema examples
class JobPostingEntity(BaseModel):
    """Custom schema for job postings."""

    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: Optional[str] = Field(None, description="Job location")
    salary_range: Optional[str] = Field(None, description="Salary range")
    requirements: List[str] = Field(
        default_factory=list,
        description="List of job requirements"
    )


class ResearchPaperEntity(BaseModel):
    """Custom schema for research papers."""

    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(
        default_factory=list,
        description="List of authors"
    )
    year: Optional[int] = Field(None, description="Publication year", ge=1900, le=2100)
    venue: Optional[str] = Field(None, description="Publication venue")
    citations: Optional[int] = Field(None, description="Number of citations", ge=0)


async def example_1_custom_schema_extraction():
    """
    Example 1: Extract entities using custom Pydantic schemas.

    Demonstrates how to define your own entity types for domain-specific extraction.
    """
    print("\n" + "=" * 60)
    print("Example 1: Custom Schema Extraction")
    print("=" * 60)

    job_posting_text = """
    We are looking for a Senior Machine Learning Engineer to join our team at TechCorp.
    The position is based in San Francisco, CA with a hybrid work model.
    Salary range: $150,000 - $200,000 per year.

    Requirements:
    - 5+ years of experience in machine learning
    - Proficiency in Python and TensorFlow
    - Experience with large language models
    - PhD in Computer Science or related field preferred
    """

    print(f"\nInput text (Job Posting):\n{job_posting_text}")

    service = ExtractionService()

    # Extract using custom schema
    jobs = await service.extract_with_custom_schema(
        job_posting_text,
        JobPostingEntity
    )

    print(f"\nExtracted {len(jobs)} job posting(s):")
    for job in jobs:
        print(f"\n  Title: {job.title}")
        print(f"  Company: {job.company}")
        print(f"  Location: {job.location}")
        print(f"  Salary: {job.salary_range}")
        print(f"  Requirements:")
        for req in job.requirements:
            print(f"    - {req}")

    # Research paper example
    paper_text = """
    Attention Is All You Need by Vaswani et al. was published in 2017
    at the Neural Information Processing Systems conference (NeurIPS).
    The paper has been cited over 50,000 times and introduced the
    Transformer architecture that revolutionized natural language processing.
    """

    print(f"\nInput text (Research Paper):\n{paper_text}")

    papers = await service.extract_with_custom_schema(
        paper_text,
        ResearchPaperEntity
    )

    print(f"\nExtracted {len(papers)} paper(s):")
    for paper in papers:
        print(f"\n  Title: {paper.title}")
        print(f"  Authors: {', '.join(paper.authors)}")
        print(f"  Year: {paper.year}")
        print(f"  Venue: {paper.venue}")
        print(f"  Citations: {paper.citations}")


async def example_2_relationship_extraction():
    """
    Example 2: Extract relationships between entities.

    Demonstrates how to identify how entities are related to each other.
    """
    print("\n" + "=" * 60)
    print("Example 2: Relationship Extraction")
    print("=" * 60)

    text = """
    John Smith works at Google as a software engineer.
    He reports to Jane Doe, who is the Engineering Manager.
    Google was founded by Larry Page and Sergey Brin in 1998.
    The company is headquartered in Mountain View, California.
    """

    print(f"\nInput text:\n{text}")

    service = ExtractionService()
    relationships = await service.extract_relations(text)

    print(f"\nExtracted {len(relationships)} relationship(s):")
    for rel in relationships:
        print(f"\n  {rel.source_entity} --[{rel.relationship_type}]--> {rel.target_entity}")
        if rel.context:
            print(f"  Context: {rel.context}")


async def example_3_batch_processing():
    """
    Example 3: Batch processing multiple texts.

    Demonstrates how to efficiently process multiple documents.
    """
    print("\n" + "=" * 60)
    print("Example 3: Batch Processing")
    print("=" * 60)

    texts = [
        "Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in 1976.",
        "Microsoft is headquartered in Redmond, Washington and was founded by Bill Gates.",
        "Amazon was founded by Jeff Bezos in 1994 and is based in Seattle, Washington.",
    ]

    print(f"\nProcessing {len(texts)} texts in parallel...")

    service = ExtractionService()
    batch_result = await service.extract_batch(
        texts=texts,
        schema=OrganizationEntity,
        max_concurrency=3
    )

    print(f"\nBatch Processing Results:")
    print(f"  Total texts: {batch_result.total_texts}")
    print(f"  Successful: {batch_result.successful_count}")
    print(f"  Failed: {batch_result.failed_count}")
    print(f"  Total entities extracted: {batch_result.total_entities}")
    print(f"  Total time: {batch_result.total_time_ms:.2f}ms")

    print("\nExtracted organizations from each text:")
    for i, result in enumerate(batch_result.results, 1):
        if result.success:
            print(f"\n  Text {i}:")
            for org in result.entities:
                print(f"    - {org.name} (founded: {org.founded_year})")


async def example_4_complex_text_extraction():
    """
    Example 4: Extract from complex, multi-entity text.

    Demonstrates extraction from real-world text with multiple entity types.
    """
    print("\n" + "=" * 60)
    print("Example 4: Complex Multi-Entity Text")
    print("=" * 60)

    text = """
    The annual TechCrunch Disrupt conference was held in San Francisco in September 2023.
    Keynote speakers included Sundar Pichai (CEO of Google) and Satya Nadella (CEO of Microsoft).
    Google announced the Pixel 8 Pro smartphone priced at $999, featuring their new Tensor G3 chip.
    Microsoft unveiled updates to their Azure cloud platform and Copilot AI assistant.
    The event attracted over 10,000 attendees from 50 different countries.
    """

    print(f"\nInput text:\n{text}")

    service = ExtractionService()
    entities = await service.extract_all(text)

    print("\nExtracted entities:")

    if entities["persons"]:
        print(f"\n  Persons ({len(entities['persons'])}):")
        for person in entities["persons"]:
            details = []
            if person.title:
                details.append(f"title: {person.title}")
            if person.organization:
                details.append(f"org: {person.organization}")
            print(f"    - {person.name}" + (f" ({', '.join(details)})" if details else ""))

    if entities["organizations"]:
        print(f"\n  Organizations ({len(entities['organizations'])}):")
        for org in entities["organizations"]:
            print(f"    - {org.name}")

    if entities["products"]:
        print(f"\n  Products ({len(entities['products'])}):")
        for product in entities["products"]:
            price = f"${product.price}" if product.price else "N/A"
            print(f"    - {product.name} ({price})")

    if entities["events"]:
        print(f"\n  Events ({len(entities['events'])}):")
        for event in entities["events"]:
            location = f" @ {event.location}" if event.location else ""
            date = f" ({event.date})" if event.date else ""
            print(f"    - {event.name}{date}{location}")

    if entities["locations"]:
        print(f"\n  Locations ({len(entities['locations'])}):")
        for location in entities["locations"]:
            print(f"    - {location.name}")


async def example_5_synchronous_api():
    """
    Example 5: Using the synchronous API.

    Demonstrates the synchronous wrapper methods for easier integration.
    """
    print("\n" + "=" * 60)
    print("Example 5: Synchronous API")
    print("=" * 60)

    text = """
    Elon Musk is the CEO of Tesla, Inc., an electric vehicle company
    founded in 2003 and headquartered in Austin, Texas.
    """

    print(f"\nInput text:\n{text}")

    service = ExtractionService()

    # Use synchronous API
    entities = service.extract_all_sync(text)

    print("\nExtracted entities (synchronous API):")
    for entity_type, entity_list in entities.items():
        if entity_list:
            print(f"\n  {entity_type.capitalize()}:")
            for entity in entity_list[:3]:  # Show first 3
                print(f"    - {entity.name if hasattr(entity, 'name') else entity}")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("LangChain Entity Extraction - Advanced Examples")
    print("=" * 60)

    try:
        await example_1_custom_schema_extraction()
        await example_2_relationship_extraction()
        await example_3_batch_processing()
        await example_4_complex_text_extraction()
        await example_5_synchronous_api()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
