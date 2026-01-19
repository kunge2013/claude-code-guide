"""Baidu NetDisk file scanner using Playwright."""

import json
import time
from playwright.sync_api import Page


class BaiduNetDiskScanner:
    """Baidu网盘文件扫描器 - 用户手动登录后扫描文件和分享"""

    def __init__(self, page: Page):
        self.page = page
        self.base_url = "https://pan.baidu.com/"

    def navigate_to_target(self, target_url: str):
        """导航到目标路径"""
        print(f"正在导航到目标路径: {target_url}")
        self.page.goto(target_url, wait_until='domcontentloaded', timeout=60000)
        self.page.wait_for_timeout(3000)
        print(f"当前URL: {self.page.url}")

    def wait_for_user_login(self, timeout=300):
        """等待用户手动登录完成"""
        print("\n" + "="*50)
        print("请在浏览器窗口中手动完成登录...")
        print(f"等待时间: {timeout}秒")
        print("="*50 + "\n")

        start_time = time.time()
        while (time.time() - start_time) < timeout:
            # 检查是否已登录（URL包含disk或main）
            current_url = self.page.url
            if 'disk' in current_url or 'main' in current_url:
                # 再检查是否有退出按钮，确认登录成功
                if self.page.locator('text=退出').count() > 0:
                    print("\n检测到登录成功！")
                    return True

            self.page.wait_for_timeout(1000)

        print("\n等待登录超时")
        return False

    def get_folder_list(self):
        """获取当前路径下的文件夹列表（精确方法）"""
        print("\n正在获取文件夹列表...")
        self.page.wait_for_timeout(3000)

        folders = set()

        # 使用之前成功的选择器
        file_selectors = [
            '[class*="file-item"]',
            '[class*="file-item-name"]',
            '[class*="file-name"]',
            'div[class*="file"]',
            'span[class*="name"]',
        ]

        for selector in file_selectors:
            try:
                elements = self.page.locator(selector).all()
                print(f"选择器 '{selector}' 找到 {len(elements)} 个元素")

                for elem in elements:
                    try:
                        if elem.is_visible():
                            text = elem.inner_text()
                            if text and text.strip():
                                name = text.strip()
                                if self._is_valid_folder_name(name):
                                    folders.add(name)
                    except:
                        pass

                if len(folders) >= 5:
                    break
            except:
                pass

        result = sorted(list(folders))
        print(f"找到 {len(result)} 个有效文件夹")
        return result

    def _is_valid_folder_name(self, name):
        """判断是否是有效的文件夹名称"""
        if not name or len(name) < 2:
            return False

        # 过滤掉菜单项和UI元素
        invalid_names = [
            '重命名', '复制', '移动', '删除', '分享', '下载', '导出文件目录',
            '共享', '新建文件夹', '新建笔记', '云添加', '智能PPT', '打开电脑端',
            '添加链接任务', '添加BT任务', '一键生成PPT，匹配海量模板',
            '返回上一级', '列表模式', '缩略模式', '大图模式', '展开',
            '我的文件', '图片', '文档', '视频', '种子', '音频', '其它',
            '个人主页', '帮助中心', '退出登录', '快捷访问',
            '5T空间 极速下载 视频倍速 查看更多',
            '云添加清除记录', '流畅播清除记录', '清除记录',
            '云添加列表为空', '流畅播列表为空',
            '- 仅展示本次上传任务 -', '-'
        ]

        if name in invalid_names:
            return False

        # 过滤掉包含特殊符号的菜单项
        if '|' in name and '全部文件' in name:
            return False

        # 过滤掉纯数字日期格式（如 2025-10-22，这个可能是文件夹，保留）
        # 过滤掉单字符
        if len(name) == 1 and name in '-+|>':
            return False

        return True

    def select_folder(self, folder_name):
        """选中指定文件夹"""
        print(f"  正在选中: {folder_name}")

        # 尝试通过文本查找并点击选中
        try:
            # 查找包含该文件夹名的元素
            selectors = [
                f'span:has-text("{folder_name}")',
                f'div:has-text("{folder_name}")',
                f'a:has-text("{folder_name}")',
            ]

            for selector in selectors:
                try:
                    elem = self.page.locator(selector).first
                    if elem.count() > 0 and elem.is_visible():
                        # 右键点击或悬停来显示选中状态
                        elem.click(button='right')
                        time.sleep(0.5)
                        return True
                except:
                    pass

            # 尝试通过XPath查找
            xpath = f"//span[contains(text(), '{folder_name}')]"
            elem = self.page.locator(f"xpath={xpath}").first
            if elem.count() > 0 and elem.is_visible():
                elem.click(button='right')
                time.sleep(0.5)
                return True

        except Exception as e:
            print(f"    选中失败: {e}")

        return False

    def share_folder(self, folder_name):
        """分享指定文件夹，返回分享链接和提取码"""
        print(f"\n正在分享: {folder_name}")

        # 先刷新页面确保状态正确
        self.page.wait_for_timeout(500)

        # 1. 选中文件夹
        if not self.select_folder(folder_name):
            print(f"  无法选中文件夹: {folder_name}")
            return None

        # 2. 点击分享按钮
        try:
            # 分享按钮可能在右键菜单中，也可能在顶部工具栏
            share_selectors = [
                'text=分享',
                'button:has-text("分享")',
                'a:has-text("分享")',
                '[class*="share"]',
            ]

            clicked = False
            for selector in share_selectors:
                try:
                    share_btn = self.page.locator(selector).first
                    if share_btn.count() > 0 and share_btn.is_visible():
                        share_btn.click()
                        clicked = True
                        time.sleep(2)
                        break
                except:
                    pass

            if not clicked:
                print(f"  未找到分享按钮")
                return None

            # 3. 等待分享弹窗出现
            time.sleep(2)

            # 4. 选择创建公开链接（永久分享）
            try:
                # 查找"创建公开链接"或"公开分享"选项
                public_link_selectors = [
                    'text=创建公开链接',
                    'text=公开分享',
                    'text=永久链接',
                    '[class*="public"]',
                    'input[type="radio"]',
                ]

                for selector in public_link_selectors:
                    try:
                        elem = self.page.locator(selector).first
                        if elem.count() > 0 and elem.is_visible():
                            elem.click()
                            time.sleep(0.5)
                            break
                    except:
                        pass

            except:
                pass

            # 5. 点击创建链接/确定按钮
            try:
                create_selectors = [
                    'button:has-text("创建链接")',
                    'button:has-text("确定")',
                    'button:has-text("分享")',
                    'a:has-text("创建链接")',
                ]

                for selector in create_selectors:
                    try:
                        create_btn = self.page.locator(selector).first
                        if create_btn.count() > 0 and create_btn.is_visible():
                            create_btn.click()
                            time.sleep(2)
                            break
                    except:
                        pass

            except:
                pass

            # 6. 获取分享链接和提取码
            time.sleep(2)

            share_link = None
            share_code = None

            # 尝试获取分享链接
            try:
                link_input = self.page.locator('input[type="text"], input[class*="link"], input[class*="url"]').first
                if link_input.count() > 0:
                    share_link = link_input.input_value()
                    print(f"  分享链接: {share_link}")
            except:
                pass

            # 尝试获取提取码
            try:
                code_elem = self.page.locator('span[class*="code"], span[class*="pwd"], div[class*="code"]').first
                if code_elem.count() > 0:
                    share_code = code_elem.inner_text().strip()
                    print(f"  提取码: {share_code}")
            except:
                pass

            # 如果没有找到提取码，尝试从页面文本中提取
            if not share_code:
                try:
                    page_text = self.page.inner_text('body')
                    # 查找提取码模式（通常是4位字符）
                    import re
                    code_match = re.search(r'提取码[：:]\s*([a-zA-Z0-9]{4})', page_text)
                    if code_match:
                        share_code = code_match.group(1)
                        print(f"  提取码: {share_code}")
                except:
                    pass

            # 7. 关闭分享弹窗
            try:
                close_selectors = [
                    'button:has-text("关闭")',
                    '[class*="close"]',
                    'text=✕',
                ]
                for selector in close_selectors:
                    try:
                        close_btn = self.page.locator(selector).first
                        if close_btn.count() > 0 and close_btn.is_visible():
                            close_btn.click()
                            time.sleep(0.5)
                            break
                    except:
                        pass
            except:
                pass

            # 点击空白处取消选中
            try:
                self.page.click('body')
                time.sleep(0.5)
            except:
                pass

            if share_link:
                return {
                    'name': folder_name,
                    'share_link': share_link,
                    'share_code': share_code or '',
                    'full_link': f"{share_link} 提取码: {share_code}" if share_code else share_link
                }

        except Exception as e:
            print(f"  分享出错: {e}")

        return None

    def share_all_folders(self, folders):
        """批量分享所有文件夹"""
        results = []

        print("\n" + "="*50)
        print(f"开始分享 {len(folders)} 个文件夹")
        print("="*50)

        for i, folder in enumerate(folders, 1):
            print(f"\n[{i}/{len(folders)}] ", end="")

            result = self.share_folder(folder)
            if result:
                results.append(result)
                print(f"  ✓ 分享成功")

            # 避免操作过快
            time.sleep(2)

        return results

    def print_share_results(self, results):
        """打印分享结果"""
        print("\n" + "="*50)
        print(f"分享完成！成功分享 {len(results)} 个文件夹")
        print("="*50)

        for i, r in enumerate(results, 1):
            print(f"\n{i}. {r['name']}")
            print(f"   链接: {r['share_link']}")
            if r['share_code']:
                print(f"   提取码: {r['share_code']}")

        print("\n" + "="*50 + "\n")

    def save_share_results(self, results, output_file='share_links.json'):
        """保存分享结果到文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"分享链接已保存到: {output_file}")

    def save_share_results_as_text(self, results, output_file='share_links.txt'):
        """保存分享结果为文本格式"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("="*50 + "\n")
            f.write(f"百度网盘分享链接 - 共 {len(results)} 个\n")
            f.write("="*50 + "\n\n")

            for i, r in enumerate(results, 1):
                f.write(f"{i}. {r['name']}\n")
                f.write(f"   链接: {r['share_link']}\n")
                if r['share_code']:
                    f.write(f"   提取码: {r['share_code']}\n")
                f.write(f"   完整: {r['full_link']}\n")
                f.write("\n")

        print(f"分享链接（文本格式）已保存到: {output_file}")
