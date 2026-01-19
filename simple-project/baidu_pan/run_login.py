"""百度网盘文件分享器 - 手动登录后分享指定路径的所有文件夹"""

import sys
import os
import time
import argparse
from playwright.sync_api import sync_playwright
from config import Config
from baidu_login import BaiduNetDiskScanner


def main():
    """主函数"""
    # 支持命令行参数覆盖配置
    parser = argparse.ArgumentParser(description='百度网盘文件分享器')
    parser.add_argument(
        '--path',
        type=str,
        help='目标路径（例如: /简历/上千套简历模板）',
        default=None
    )
    parser.add_argument(
        '--output',
        type=str,
        help='输出文件名（默认: share_links.json）',
        default='share_links.json'
    )
    parser.add_argument(
        '--fresh-login',
        action='store_true',
        help='清除已保存的登录状态，重新登录'
    )
    args = parser.parse_args()

    config = Config()

    # 命令行参数优先级高于配置文件
    target_path = args.path if args.path else config.target_path

    # 使用配置类的target_url属性来正确编码路径
    if args.path:
        from urllib.parse import quote
        encoded_path = quote(target_path.encode('utf-8'))
        target_url = f"{Config.BASE_URL}disk/main#/index?category=all&path={encoded_path}"
    else:
        target_url = config.target_url

    print("="*50)
    print("百度网盘文件分享器")
    print("="*50)
    print(f"目标路径: {target_path}")
    print(f"目标URL: {target_url}")
    print("="*50)

    # 用户数据目录，用于保存登录状态
    user_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.browser_data')

    # 如果要求重新登录，删除已保存的数据
    if args.fresh_login:
        import shutil
        if os.path.exists(user_data_dir):
            shutil.rmtree(user_data_dir)
            print("已清除保存的登录状态\n")

    with sync_playwright() as p:
        # 使用持久化上下文，保存登录状态
        browser_context = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
            ]
        )

        # 获取或创建页面
        if len(browser_context.pages) > 0:
            page = browser_context.pages[0]
        else:
            page = browser_context.new_page()

        try:
            scanner = BaiduNetDiskScanner(page)

            # 1. 先导航到百度网盘首页
            print("\n正在打开百度网盘...")
            page.goto(Config.BASE_URL, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(2000)

            # 2. 检查是否已经登录
            current_url = page.url
            is_logged_in = ('disk' in current_url or 'main' in current_url) and page.locator('text=退出').count() > 0

            if is_logged_in:
                print("✓ 检测到已登录状态！")
            else:
                print("未检测到登录状态，请手动登录...")
                login_success = scanner.wait_for_user_login(timeout=300)

                if not login_success:
                    print("\n登录超时或失败，程序退出")
                    browser_context.close()
                    return

            # 3. 导航到目标路径
            print(f"\n正在导航到目标路径: {target_path}")
            scanner.navigate_to_target(target_url)

            # 4. 获取文件夹列表
            folders = scanner.get_folder_list()

            if not folders:
                print("\n未找到任何文件夹，程序退出")
                browser_context.close()
                return

            # 5. 显示找到的文件夹列表
            print("\n找到以下文件夹:")
            for i, folder in enumerate(folders, 1):
                print(f"  {i}. {folder}")

            # 6. 询问是否继续
            print(f"\n即将开始分享 {len(folders)} 个文件夹...")
            print("按 Ctrl+C 可随时中断\n")

            time.sleep(2)

            # 7. 批量分享所有文件夹
            results = scanner.share_all_folders(folders)

            # 8. 打印结果
            scanner.print_share_results(results)

            # 9. 保存到文件
            base_name = args.output.rsplit('.', 1)[0]
            json_file = f"{base_name}.json"
            txt_file = f"{base_name}.txt"

            scanner.save_share_results(results, json_file)
            scanner.save_share_results_as_text(results, txt_file)

            print("\n分享完成！浏览器将保持打开状态，按 Ctrl+C 退出...")
            print("或直接关闭浏览器窗口\n")

            # 保持浏览器打开，直到用户主动关闭
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n\n用户中断，正在关闭浏览器...")

        except KeyboardInterrupt:
            print("\n\n用户中断，正在关闭浏览器...")

        except Exception as e:
            print(f"\n发生错误: {e}")
            import traceback
            traceback.print_exc()

        finally:
            try:
                browser_context.close()
            except:
                pass


if __name__ == "__main__":
    main()
