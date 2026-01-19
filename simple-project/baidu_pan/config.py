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
        # 目标路径，默认为简历/上千套简历模板，不定期更新
        self.target_path = os.getenv(
            'BAIDU_TARGET_PATH',
            '/简历/上千套简历模板，不定期更新'
        )

    @property
    def target_url(self):
        """获取目标路径的完整URL"""
        from urllib.parse import quote
        encoded_path = quote(self.target_path.encode('utf-8'))
        return f"{self.BASE_URL}disk/main#/index?category=all&path={encoded_path}"

    def validate(self):
        """配置验证（不再强制要求登录凭据）"""
        return True
