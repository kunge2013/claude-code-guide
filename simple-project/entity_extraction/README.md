# LangChain Entity Extraction

A reference implementation for entity extraction using LangChain, based on the official documentation: [https://python.langchain.com.cn/docs/modules/chains/additional/extraction](https://python.langchain.com.cn/docs/modules/chains/additional/extraction)

## Features

- **Two Extraction Methods**:
  - Schema-based extraction using dictionary definitions
  - Pydantic-based extraction with type safety and validation (recommended)

- **Multiple Entity Types**:
  - Person (name, age, title, organization, email, phone, skills)
  - Organization (name, industry, founded year, headquarters, website)
  - Product (name, price, currency, category, features, manufacturer)
  - Location (name, type, country, region)
  - Event (name, date, location, participants)

- **Relationship Extraction**: Extract relationships between entities

- **Multiple LLM Providers**:
  - OpenAI (GPT-4, GPT-3.5)
  - ZhipuAI (GLM-4)

- **Batch Processing**: Efficiently process multiple texts in parallel

## Installation

```bash
# Clone the repository
cd /path/to/entity_extraction

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the environment variable template:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API keys:

```bash
# For OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# OR for ZhipuAI
ZHIPUAI_API_KEY=your_zhipuai_api_key
ZHIPUAI_API_BASE=https://open.bigmodel.cn/api/paas/v4
ZHIPUAI_MODEL=glm-4
```

3. Configure extraction settings in `config/extraction_config.yaml`:

```yaml
extraction:
  strategy: pydantic  # Options: pydantic, schema, hybrid
  llm:
    provider: openai
    model: gpt-4
    temperature: 0.0
```

## Quick Start

### Basic Usage

```python
import asyncio
from langchain_entity_extraction import ExtractionService

async def main():
    # Initialize service
    service = ExtractionService()

    # Extract person entities
    text = "John Smith is a 35-year-old software engineer at Google."
    persons = await service.extract_persons(text)

    for person in persons:
        print(f"Name: {person.name}")
        print(f"Age: {person.age}")
        print(f"Title: {person.title}")
        print(f"Organization: {person.organization}")

asyncio.run(main())
```

### Extract All Entity Types

```python
service = ExtractionService()
text = """
John Smith works at Google in Mountain View, CA.
He's working on the Pixel 8 Pro which costs $999.
"""

entities = await service.extract_all(text)

# Access different entity types
print(f"Persons: {entities['persons']}")
print(f"Organizations: {entities['organizations']}")
print(f"Products: {entities['products']}")
print(f"Locations: {entities['locations']}")
```

### Using Schema-Based Extraction

```python
# Define custom schema
schema = {
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "email": {"type": "string"}
    },
    "required": ["name"]
}

service = ExtractionService()
persons = await service.extract_persons(text, use_schema=True)
```

### Custom Entity Schema

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class JobPosting(BaseModel):
    """Custom job posting schema."""
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    salary: Optional[str] = Field(None, description="Salary range")
    requirements: List[str] = Field(
        default_factory=list,
        description="Job requirements"
    )

service = ExtractionService()
jobs = await service.extract_with_custom_schema(text, JobPosting)
```

### Batch Processing

```python
texts = [
    "Apple was founded by Steve Jobs in 1976.",
    "Microsoft was founded by Bill Gates in 1975.",
    "Google was founded by Larry Page in 1998."
]

batch_result = await service.extract_batch(
    texts=texts,
    schema=OrganizationEntity,
    max_concurrency=3
)

print(f"Processed: {batch_result.successful_count}/{batch_result.total_texts}")
print(f"Total entities: {batch_result.total_entities}")
```

### Relationship Extraction

```python
text = "John Smith works at Google as a software engineer."

service = ExtractionService()
relationships = await service.extract_relations(text)

for rel in relationships:
    print(f"{rel.source_entity} --[{rel.relationship_type}]--> {rel.target_entity}")
```

## Running Examples

### Basic Examples
```bash
python scripts/basic_extraction.py
```

Demonstrates:
- Person extraction (Pydantic and Schema)
- Organization extraction
- Product extraction
- Extract all entity types

### Advanced Examples
```bash
python scripts/advanced_extraction.py
```

Demonstrates:
- Custom schema extraction
- Relationship extraction
- Batch processing
- Complex multi-entity text
- Synchronous API usage

## Project Structure

```
entity_extraction/
├── config/
│   └── extraction_config.yaml       # Extraction configuration
├── src/langchain_entity_extraction/
│   ├── config/
│   │   └── settings.py              # Configuration loader
│   ├── models/
│   │   ├── entity_schemas.py        # Pydantic entity models
│   │   └── extraction_result.py     # Result models
│   ├── extractors/
│   │   ├── base_extractor.py        # Base extractor interface
│   │   ├── schema_extractor.py      # Schema-based extraction
│   │   ├── pydantic_extractor.py    # Pydantic-based extraction
│   │   └── relation_extractor.py    # Relationship extraction
│   ├── llm/
│   │   └── langchain_llm.py         # LLM factory
│   ├── services/
│   │   └── extraction_service.py    # High-level API
│   └── utils/
│       └── logger.py                # Logging utilities
├── scripts/
│   ├── basic_extraction.py          # Basic examples
│   └── advanced_extraction.py       # Advanced examples
└── tests/
    ├── test_extractors.py
    └── test_schemas.py
```

## API Reference

### ExtractionService

Main service class for entity extraction.

#### Methods

- `extract_persons(text, use_schema=False)` - Extract person entities
- `extract_organizations(text, use_schema=False)` - Extract organization entities
- `extract_products(text, use_schema=False)` - Extract product entities
- `extract_locations(text, use_schema=False)` - Extract location entities
- `extract_events(text, use_schema=False)` - Extract event entities
- `extract_relations(text, entity_types=None)` - Extract relationships
- `extract_all(text, use_schema=False)` - Extract all entity types
- `extract_batch(texts, schema, max_concurrency=5)` - Batch processing
- `extract_with_custom_schema(text, schema)` - Custom schema extraction
- `extract_*_sync(...)` - Synchronous wrappers

### Entity Models

#### PersonEntity
```python
class PersonEntity(BaseModel):
    name: str
    age: Optional[int]
    title: Optional[str]
    organization: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    skills: List[str]
```

#### OrganizationEntity
```python
class OrganizationEntity(BaseModel):
    name: str
    industry: Optional[str]
    founded_year: Optional[int]
    headquarters: Optional[str]
    website: Optional[str]
```

#### ProductEntity
```python
class ProductEntity(BaseModel):
    name: str
    price: Optional[float]
    currency: Optional[str]
    category: Optional[str]
    features: List[str]
    manufacturer: Optional[str]
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | - |
| `OPENAI_API_BASE` | OpenAI API base URL | https://api.openai.com/v1 |
| `OPENAI_MODEL` | OpenAI model name | gpt-4 |
| `ZHIPUAI_API_KEY` | ZhipuAI API key | - |
| `ZHIPUAI_API_BASE` | ZhipuAI API base URL | https://open.bigmodel.cn/api/paas/v4 |
| `ZHIPUAI_MODEL` | ZhipuAI model name | glm-4 |
| `LLM_PROVIDER` | LLM provider | openai |
| `EXTRACTION_TEMPERATURE` | LLM temperature | 0.0 |
| `LOG_LEVEL` | Logging level | INFO |

### YAML Configuration

See `config/extraction_config.yaml` for full configuration options including:
- Extraction strategy
- Entity type definitions
- Validation settings
- Relationship types

## Best Practices

1. **Use Pydantic Extraction**: Prefer Pydantic-based extraction for type safety and validation
2. **Batch Processing**: Use `extract_batch()` for processing multiple texts
3. **Custom Schemas**: Define custom schemas for domain-specific entities
4. **Error Handling**: Check `ExtractionResult.success` and handle errors
5. **Temperature Settings**: Use low temperature (0.0) for consistent extraction

## Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src/langchain_entity_extraction
```

## License

MIT License

## References

- [LangChain Entity Extraction Documentation](https://python.langchain.com.cn/docs/modules/chains/additional/extraction)
- [LangChain Documentation](https://python.langchain.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
