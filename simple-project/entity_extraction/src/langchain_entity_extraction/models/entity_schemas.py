"""Pydantic entity schemas for extraction."""

from typing import Optional, List
from pydantic import BaseModel, Field


class PersonEntity(BaseModel):
    """Person entity extracted from text.

    Represents information about a person including their name,
    demographics, contact information, and professional details.
    """

    name: str = Field(..., description="Full name of the person")
    age: Optional[int] = Field(
        None, description="Age in years", ge=0, le=150
    )
    title: Optional[str] = Field(
        None, description="Job title or position"
    )
    organization: Optional[str] = Field(
        None, description="Company or organization name"
    )
    email: Optional[str] = Field(
        None, description="Email address"
    )
    phone: Optional[str] = Field(
        None, description="Phone number"
    )
    skills: List[str] = Field(
        default_factory=list, description="List of skills or expertise"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "name": "John Smith",
                "age": 35,
                "title": "Software Engineer",
                "organization": "Google",
                "email": "john.smith@example.com",
                "skills": ["Python", "Machine Learning"]
            }
        }


class OrganizationEntity(BaseModel):
    """Organization entity extracted from text.

    Represents information about a company, institution,
    or other organization.
    """

    name: str = Field(..., description="Organization name")
    industry: Optional[str] = Field(
        None, description="Industry sector"
    )
    founded_year: Optional[int] = Field(
        None,
        description="Year founded",
        ge=1800,
        le=2100
    )
    headquarters: Optional[str] = Field(
        None, description="Headquarters location"
    )
    website: Optional[str] = Field(
        None, description="Company website URL"
    )
    description: Optional[str] = Field(
        None, description="Brief description of the organization"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "name": "Google",
                "industry": "Technology",
                "founded_year": 1998,
                "headquarters": "Mountain View, California",
                "website": "https://www.google.com"
            }
        }


class ProductEntity(BaseModel):
    """Product entity extracted from text.

    Represents information about a product including
    name, price, category, and features.
    """

    name: str = Field(..., description="Product name")
    price: Optional[float] = Field(
        None, description="Price in currency", ge=0
    )
    currency: Optional[str] = Field(
        default="USD", description="Currency code (e.g., USD, EUR, CNY)"
    )
    category: Optional[str] = Field(
        None, description="Product category"
    )
    features: List[str] = Field(
        default_factory=list, description="Product features"
    )
    manufacturer: Optional[str] = Field(
        None, description="Manufacturer or brand"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "name": "iPhone 15 Pro",
                "price": 999.99,
                "currency": "USD",
                "category": "Smartphone",
                "features": ["5G", "A17 Pro chip", "Titanium design"],
                "manufacturer": "Apple"
            }
        }


class LocationEntity(BaseModel):
    """Location entity extracted from text.

    Represents geographic locations including cities,
    countries, addresses, and landmarks.
    """

    name: str = Field(..., description="Location name")
    type: Optional[str] = Field(
        None,
        description="Type of location (city, country, address, landmark, etc.)"
    )
    country: Optional[str] = Field(
        None, description="Country name"
    )
    region: Optional[str] = Field(
        None, description="Region, state, or province"
    )
    coordinates: Optional[str] = Field(
        None, description="GPS coordinates or spatial reference"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "name": "San Francisco",
                "type": "city",
                "country": "United States",
                "region": "California"
            }
        }


class EventEntity(BaseModel):
    """Event entity extracted from text.

    Represents events with temporal and spatial information,
    including participants and descriptions.
    """

    name: str = Field(..., description="Event name")
    date: Optional[str] = Field(
        None, description="Event date or date range"
    )
    location: Optional[str] = Field(
        None, description="Event location"
    )
    participants: List[str] = Field(
        default_factory=list, description="Event participants or attendees"
    )
    description: Optional[str] = Field(
        None, description="Event description or summary"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "name": "Python Conference 2024",
                "date": "2024-05-15",
                "location": "San Francisco, CA",
                "participants": ["John Smith", "Jane Doe"],
                "description": "Annual Python developers conference"
            }
        }


class EntityRelationship(BaseModel):
    """Relationship between two entities.

    Represents how entities are connected or related to each other.
    """

    source_entity: str = Field(
        ..., description="Name of the source entity"
    )
    target_entity: str = Field(
        ..., description="Name of the target entity"
    )
    relationship_type: str = Field(
        ..., description="Type of relationship (works_at, knows, etc.)"
    )
    context: Optional[str] = Field(
        None, description="Context describing the relationship"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "source_entity": "John Smith",
                "target_entity": "Google",
                "relationship_type": "works_at",
                "context": "John Smith works as a software engineer at Google"
            }
        }
