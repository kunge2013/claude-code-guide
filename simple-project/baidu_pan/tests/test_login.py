"""Test cases for Baidu NetDisk login automation."""

import pytest
from playwright.sync_api import Page
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from baidu_login import BaiduNetDiskLogin
from config import Config


def test_baidu_netdisk_login(page: Page):
    """Test Baidu NetDisk login automation."""
    config = Config()
    config.validate()

    login = BaiduNetDiskLogin(page)
    result = login.login(config.phone, config.password)

    # Verify login success
    assert result is True or "pan.baidu.com" in page.url
