"""Tests for entity schema models."""

import pytest
from pydantic import ValidationError

from langchain_entity_extraction.models.entity_schemas import (
    PersonEntity,
    OrganizationEntity,
    ProductEntity,
    LocationEntity,
    EventEntity,
    EntityRelationship,
)


class TestPersonEntity:
    """Tests for PersonEntity model."""

    def test_valid_person(self):
        """Test creating a valid person."""
        person = PersonEntity(
            name="John Smith",
            age=35,
            title="Software Engineer",
            organization="Google",
            email="john@example.com"
        )
        assert person.name == "John Smith"
        assert person.age == 35
        assert person.title == "Software Engineer"
        assert person.organization == "Google"

    def test_person_with_skills(self):
        """Test person with skills."""
        person = PersonEntity(
            name="Jane Doe",
            skills=["Python", "Machine Learning", "SQL"]
        )
        assert len(person.skills) == 3
        assert "Python" in person.skills

    def test_age_validation(self):
        """Test age validation constraints."""
        # Valid age
        person = PersonEntity(name="Test", age=25)
        assert person.age == 25

        # Invalid age (too high)
        with pytest.raises(ValidationError):
            PersonEntity(name="Test", age=200)

        # Invalid age (negative)
        with pytest.raises(ValidationError):
            PersonEntity(name="Test", age=-5)


class TestOrganizationEntity:
    """Tests for OrganizationEntity model."""

    def test_valid_organization(self):
        """Test creating a valid organization."""
        org = OrganizationEntity(
            name="Google",
            industry="Technology",
            founded_year=1998,
            headquarters="Mountain View, CA"
        )
        assert org.name == "Google"
        assert org.industry == "Technology"
        assert org.founded_year == 1998

    def test_year_validation(self):
        """Test year validation constraints."""
        # Valid year
        org = OrganizationEntity(
            name="Test Corp",
            founded_year=2020
        )
        assert org.founded_year == 2020

        # Invalid year (too early)
        with pytest.raises(ValidationError):
            OrganizationEntity(
                name="Test Corp",
                founded_year=1700
            )

        # Invalid year (too late)
        with pytest.raises(ValidationError):
            OrganizationEntity(
                name="Test Corp",
                founded_year=2200
            )


class TestProductEntity:
    """Tests for ProductEntity model."""

    def test_valid_product(self):
        """Test creating a valid product."""
        product = ProductEntity(
            name="iPhone 15",
            price=999.99,
            currency="USD",
            category="Smartphone"
        )
        assert product.name == "iPhone 15"
        assert product.price == 999.99
        assert product.currency == "USD"

    def test_product_with_features(self):
        """Test product with features."""
        product = ProductEntity(
            name="Laptop",
            features=["16GB RAM", "512GB SSD", "Intel i7"]
        )
        assert len(product.features) == 3

    def test_price_validation(self):
        """Test price validation (non-negative)."""
        # Valid price
        product = ProductEntity(name="Test", price=100)
        assert product.price == 100

        # Invalid price (negative)
        with pytest.raises(ValidationError):
            ProductEntity(name="Test", price=-50)


class TestLocationEntity:
    """Tests for LocationEntity model."""

    def test_valid_location(self):
        """Test creating a valid location."""
        location = LocationEntity(
            name="San Francisco",
            type="city",
            country="United States",
            region="California"
        )
        assert location.name == "San Francisco"
        assert location.type == "city"
        assert location.country == "United States"


class TestEventEntity:
    """Tests for EventEntity model."""

    def test_valid_event(self):
        """Test creating a valid event."""
        event = EventEntity(
            name="Python Conference 2024",
            date="2024-05-15",
            location="San Francisco, CA",
            participants=["John Smith", "Jane Doe"]
        )
        assert event.name == "Python Conference 2024"
        assert event.date == "2024-05-15"
        assert len(event.participants) == 2


class TestEntityRelationship:
    """Tests for EntityRelationship model."""

    def test_valid_relationship(self):
        """Test creating a valid relationship."""
        rel = EntityRelationship(
            source_entity="John Smith",
            target_entity="Google",
            relationship_type="works_at",
            context="John Smith works as a software engineer at Google"
        )
        assert rel.source_entity == "John Smith"
        assert rel.target_entity == "Google"
        assert rel.relationship_type == "works_at"
