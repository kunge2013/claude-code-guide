"""Configuration management for Baidu NetDisk automation."""

import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Configuration management for Baidu NetDisk automation."""

    BASE_URL = "https://pan.baidu.com/"

    def __init__(self):
        load_dotenv()
        self.phone = os.getenv('BAIDU_PHONE')
        self.password = os.getenv('BAIDU_PASSWORD')

    def validate(self):
        """Validate that required credentials are set."""
        if not self.phone or not self.password:
            raise ValueError(
                "Credentials not set. Please configure BAIDU_PHONE and BAIDU_PASSWORD in .env file"
            )
        return True
