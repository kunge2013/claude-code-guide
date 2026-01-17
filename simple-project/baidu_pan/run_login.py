"""运行百度网盘登录自动化（支持验证码输入）"""

import sys
import time
from playwright.sync_api import sync_playwright
from config import Config
from baidu_login import BaiduNetDiskLogin


def main():
    """主函数"""
    config = Config()
    config.validate()

    print("正在启动百度网盘登录自动化...")

    with sync_playwright() as p:
        # 启动浏览器（headful模式以显示窗口）
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            # 执行登录
            login = BaiduNetDiskLogin(page)
            result = login.login(config.phone, config.password)

            if result:
                print("\n" + "="*50)
                print("登录成功！")
                print("="*50)
            else:
                print("\n登录可能失败，请检查浏览器状态")

        except Exception as e:
            print(f"\n发生错误: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Wait before closing for user to see result
            print("\n浏览器将在5秒后关闭...")
            time.sleep(5)
            browser.close()


if __name__ == "__main__":
    main()
