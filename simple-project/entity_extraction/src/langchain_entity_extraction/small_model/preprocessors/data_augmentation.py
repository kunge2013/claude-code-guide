"""
Data Augmentation.

Utilities for generating and augmenting training data.
"""

import random
from typing import List, Dict, Any
from datetime import date


class DataAugmentation:
    """
    Data augmentation for training data.

    Generates synthetic training examples for MVP development.

    Example:
        >>> augmenter = DataAugmentation()
        >>> ner_data = augmenter.generate_ner_data(1000)
        >>> rewrite_data = augmenter.generate_rewrite_data(500)
    """

    # Product list
    PRODUCTS = ["cdn", "ecs", "oss", "rds", "slb"]

    # Time expressions
    TIME_EXPRESSIONS = {
        "今年": None,  # Will be set dynamically
        "去年": None,
        "本月": None,
        "上月": None,
        "本季度": None,
        "上季度": None,
        "最近7天": None,
    }

    # Field mappings
    FIELD_MAPPING = {
        "金额": "出账金额",
        "数量": "订单数量",
        "收入": "营业收入",
        "流量": "流量",
        "用户数": "用户数",
    }

    # Organizations
    ORGANIZATIONS = ["阿里巴巴", "腾讯", "华为", "百度", "字节跳动"]

    # Persons
    PERSONS = ["张三", "李四", "王五", "赵六", "钱七"]

    def __init__(self):
        """Initialize with current date info."""
        self._init_time_mappings()

    def _init_time_mappings(self):
        """Initialize time mappings based on current date."""
        today = date.today()
        current_year = today.year
        current_month = today.month
        current_quarter = (today.month - 1) // 3 + 1

        self.TIME_EXPRESSIONS.update({
            "今年": f"{current_year}年",
            "去年": f"{current_year - 1}年",
            "本月": f"{current_year}年{current_month}月",
            "上月": self._get_last_month_str(current_year, current_month),
            "本季度": f"{current_year}年Q{current_quarter}",
            "上季度": self._get_last_quarter_str(current_year, current_quarter),
            "最近7天": f"{current_year}-01-22至{current_year}-01-29",  # Simplified
        })

    @staticmethod
    def _get_last_month_str(year: int, month: int) -> str:
        """Get string representation of last month."""
        if month == 1:
            return f"{year - 1}年12月"
        else:
            return f"{year}年{month - 1}月"

    @staticmethod
    def _get_last_quarter_str(year: int, quarter: int) -> str:
        """Get string representation of last quarter."""
        if quarter == 1:
            return f"{year - 1}年Q4"
        else:
            return f"{year}年Q{quarter - 1}"

    def generate_ner_data(self, count: int) -> List[Dict[str, Any]]:
        """
        Generate synthetic NER training data.

        Args:
            count: Number of samples to generate

        Returns:
            List of NER samples
        """
        data = []

        templates = [
            "{time}{product}产品{field}是多少",
            "{time}{product}和{product2}的{field}",
            "{product}产品的{field}是{value}",
            "{org}的{person}负责{product}产品",
            "{person}使用{product}产品",
            "{org}推出新的{product}产品",
        ]

        for _ in range(count):
            template = random.choice(templates)

            # Random selections
            time_expr = random.choice(list(self.TIME_EXPRESSIONS.keys()))
            product = random.choice(self.PRODUCTS)
            product2 = random.choice([p for p in self.PRODUCTS if p != product])
            field = random.choice(list(self.FIELD_MAPPING.keys()))
            value = random.choice(["100", "200", "1000", "5000"])
            org = random.choice(self.ORGANIZATIONS)
            person = random.choice(self.PERSONS)

            # Generate text
            text = template.format(
                time=time_expr,
                product=product,
                product2=product2,
                field=field,
                value=value,
                org=org,
                person=person
            )

            # Generate entities
            entities = []

            # Add time entity
            if time_expr in text:
                start = text.find(time_expr)
                entities.append({
                    "entity": time_expr,
                    "label": "TIME",
                    "start": start,
                    "end": start + len(time_expr)
                })

            # Add product entities
            for prod in [product, product2]:
                if prod in text:
                    start = text.find(prod)
                    entities.append({
                        "entity": prod,
                        "label": "PRODUCT",
                        "start": start,
                        "end": start + len(prod)
                    })

            # Add field entity
            if field in text:
                start = text.find(field)
                entities.append({
                    "entity": field,
                    "label": "FIELD",
                    "start": start,
                    "end": start + len(field)
                })

            # Add org entity
            if org in text:
                start = text.find(org)
                entities.append({
                    "entity": org,
                    "label": "ORG",
                    "start": start,
                    "end": start + len(org)
                })

            # Add person entity
            if person in text:
                start = text.find(person)
                entities.append({
                    "entity": person,
                    "label": "PERSON",
                    "start": start,
                    "end": start + len(person)
                })

            data.append({
                "text": text,
                "entities": entities
            })

        return data

    def generate_rewrite_data(self, count: int) -> List[Dict[str, Any]]:
        """
        Generate synthetic rewrite training data.

        Args:
            count: Number of samples to generate

        Returns:
            List of rewrite samples
        """
        data = []

        for _ in range(count):
            # Random selections
            time_expr = random.choice(list(self.TIME_EXPRESSIONS.keys()))
            product = random.choice(self.PRODUCTS)
            field = random.choice(list(self.FIELD_MAPPING.keys()))

            # Generate input
            input_text = f"{time_expr}{product}产品{field}是多少"

            # Generate target
            time_normalized = self.TIME_EXPRESSIONS[time_expr]
            field_normalized = self.FIELD_MAPPING[field]
            target_text = f"产品ID为{product}，时间为{time_normalized}的{field_normalized}是多少"

            # Optional entities
            entities = {
                "product_id": product,
                "time": time_normalized,
                "field": field_normalized
            }

            data.append({
                "input": input_text,
                "target": target_text,
                "entities": entities
            })

        return data

    def augment_with_synonyms(
        self,
        data: List[Dict],
        augment_ratio: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Augment data with synonym replacements.

        Args:
            data: Original data
            augment_ratio: Ratio of original data to generate

        Returns:
            Augmented data list
        """
        augmented = []

        # Product synonyms (case variations)
        product_synonyms = {
            "cdn": ["CDN", "内容分发网络"],
            "ecs": ["ECS", "云服务器"],
            "oss": ["OSS", "对象存储"],
            "rds": ["RDS", "云数据库"],
            "slb": ["SLB", "负载均衡"],
        }

        # Field synonyms
        field_synonyms = {
            "金额": ["费用", "总金额", "成本"],
            "数量": ["个数", "订单数"],
            "收入": ["收益", "营收"],
        }

        num_augment = int(len(data) * augment_ratio)

        for _ in range(num_augment):
            # Sample original data
            original = random.choice(data)
            new_item = original.copy()

            # Apply random synonym replacements
            if "text" in original:
                text = original["text"]

                # Replace product
                for original_prod, synonyms in product_synonyms.items():
                    if original_prod in text:
                        synonym = random.choice(synonyms)
                        text = text.replace(original_prod, synonym, 1)
                        break

                # Replace field
                for original_field, synonyms in field_synonyms.items():
                    if original_field in text:
                        synonym = random.choice(synonyms)
                        text = text.replace(original_field, synonym, 1)
                        break

                new_item["text"] = text

                # Update entities
                if "entities" in original:
                    new_entities = []
                    for entity in original["entities"]:
                        new_entity = entity.copy()
                        new_entities.append(new_entity)
                    new_item["entities"] = new_entities

                augmented.append(new_item)

        return data + augmented

    def shuffle_entities(
        self,
        data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Shuffle entity positions in the text.

        Args:
            data: Original data

        Returns:
            Data with shuffled entity positions
        """
        # This is a simplified version
        # In production, you would want more sophisticated shuffling
        return data
