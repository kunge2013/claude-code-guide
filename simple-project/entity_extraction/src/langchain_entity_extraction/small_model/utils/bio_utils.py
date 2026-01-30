"""
BIO Tagging Utilities.

Utilities for converting between BIO (Beginning, Inside, Outside) tags
and entity spans, and for handling entity annotations.
"""

from typing import List, Dict, Tuple, Any


class BioUtils:
    """Utilities for BIO tagging format."""

    # Tag prefixes
    PREFIX_B = "B-"
    PREFIX_I = "I-"
    TAG_O = "O"

    @staticmethod
    def is_b_tag(tag: str) -> bool:
        """Check if tag is a beginning (B) tag."""
        return tag.startswith(BioUtils.PREFIX_B)

    @staticmethod
    def is_i_tag(tag: str) -> bool:
        """Check if tag is an inside (I) tag."""
        return tag.startswith(BioUtils.PREFIX_I)

    @staticmethod
    def is_o_tag(tag: str) -> bool:
        """Check if tag is outside (O) tag."""
        return tag == BioUtils.TAG_O

    @staticmethod
    def get_entity_type(tag: str) -> str:
        """
        Extract entity type from tag.

        Args:
            tag: BIO tag like "B-PERSON" or "O"

        Returns:
            Entity type string like "PERSON", or empty string for "O" tags
        """
        if BioUtils.is_o_tag(tag):
            return ""
        return tag[2:]  # Remove "B-" or "I-" prefix

    @staticmethod
    def bio_tags_to_entities(
        tokens: List[str],
        labels: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Convert BIO tags to entity spans.

        Args:
            tokens: List of tokens
            labels: List of BIO labels (same length as tokens)

        Returns:
            List of entity dicts with keys:
                - entity: the entity text
                - label: entity type
                - start: start character index
                - end: end character index
        """
        entities = []
        current_entity = None
        char_offset = 0

        for token, label in zip(tokens, labels):
            # Calculate character offset (simplified, assumes space-separated)
            start = char_offset
            end = char_offset + len(token)
            char_offset = end + 1  # +1 for space

            if BioUtils.is_b_tag(label):
                # Save previous entity if exists
                if current_entity:
                    entities.append(current_entity)

                # Start new entity
                entity_type = BioUtils.get_entity_type(label)
                current_entity = {
                    "entity": token,
                    "label": entity_type,
                    "start": start,
                    "end": end,
                }

            elif BioUtils.is_i_tag(label) and current_entity:
                # Continue current entity
                current_entity["entity"] += token
                current_entity["end"] = end

            else:
                # O tag or mismatched I tag - end current entity
                if current_entity:
                    entities.append(current_entity)
                    current_entity = None

        # Don't forget the last entity
        if current_entity:
            entities.append(current_entity)

        return entities

    @staticmethod
    def entities_to_bio_tags(
        text: str,
        entities: List[Dict[str, Any]],
        tokenizer=None
    ) -> Tuple[List[str], List[str]]:
        """
        Convert entity spans to BIO tags.

        Args:
            text: Original text
            entities: List of entity dicts with start, end, label
            tokenizer: Optional tokenizer for tokenization

        Returns:
            Tuple of (tokens, labels) with BIO tags
        """
        if tokenizer:
            tokens = tokenizer.tokenize(text)
            # Use tokenizer for proper offset mapping
            # This is a simplified version
            labels = [BioUtils.TAG_O] * len(tokens)
        else:
            # Simple whitespace tokenization
            tokens = text.split()
            labels = [BioUtils.TAG_O] * len(tokens)

        # Mark entity positions (simplified)
        for ent in entities:
            ent_type = ent["label"]
            # Find tokens that overlap with entity span
            # This is a simplified implementation
            for i, token in enumerate(tokens):
                if ent["entity"] in token or token in ent["entity"]:
                    if labels[i] == BioUtils.TAG_O:
                        labels[i] = f"{BioUtils.PREFIX_B}{ent_type}"
                    else:
                        labels[i] = f"{BioUtils.PREFIX_I}{ent_type}"

        return tokens, labels

    @staticmethod
    def validate_bio_sequence(labels: List[str]) -> bool:
        """
        Validate BIO tag sequence.

        Checks that I tags always follow B tags or I tags of the same type.

        Args:
            labels: List of BIO labels

        Returns:
            True if sequence is valid, False otherwise
        """
        prev_type = None

        for label in labels:
            if BioUtils.is_i_tag(label):
                current_type = BioUtils.get_entity_type(label)
                # I tag must follow B or I of same type
                if prev_type != current_type:
                    return False
            else:
                prev_type = BioUtils.get_entity_type(label) if BioUtils.is_b_tag(label) else None

        return True

    @staticmethod
    def merge_overlapping_entities(entities: List[Dict]) -> List[Dict]:
        """
        Merge overlapping entities (keep the longer one).

        Args:
            entities: List of entity dicts with start, end

        Returns:
            Filtered list without overlapping entities
        """
        if not entities:
            return []

        # Sort by start position
        sorted_entities = sorted(entities, key=lambda e: e["start"])
        merged = []

        for entity in sorted_entities:
            if not merged:
                merged.append(entity)
            else:
                last = merged[-1]
                # Check for overlap
                if entity["start"] < last["end"]:
                    # Keep the longer entity
                    if (entity["end"] - entity["start"]) > (last["end"] - last["start"]):
                        merged[-1] = entity
                else:
                    merged.append(entity)

        return merged
