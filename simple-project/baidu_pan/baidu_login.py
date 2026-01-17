"""Baidu NetDisk login automation using Playwright."""

from playwright.sync_api import Page


class BaiduNetDiskLogin:
    """Automated login for Baidu NetDisk."""

    def __init__(self, page: Page):
        self.page = page
        self.base_url = "https://pan.baidu.com/"

    def navigate_to_home(self):
        """Navigate to Baidu NetDisk homepage."""
        self.page.goto(self.base_url, wait_until='domcontentloaded', timeout=60000)
        # Set localStorage to use account login mode
        self.page.evaluate('window.localStorage.setItem("passLoginType", "normal")')
        # Reload for localStorage to take effect
        self.page.reload(wait_until='domcontentloaded')
        self.page.wait_for_timeout(3000)

    def click_login_button(self):
        """Click the '去登录' (Go to Login) button."""
        login_btn = self.page.get_by_text("去登录")
        login_btn.click()
        self.page.wait_for_timeout(3000)

    def select_account_login(self):
        """Select account login option in the popup."""
        self.page.wait_for_timeout(1000)
        # Try to click account login tab if still on QR mode
        try:
            account_login = self.page.get_by_text("账号登录")
            if account_login.count() > 0:
                account_login.first.click()
                self.page.wait_for_timeout(1500)
        except:
            pass

    def enter_credentials(self, phone: str, password: str):
        """Enter phone number and password."""
        # Enter phone immediately
        phone_selectors = [
            'input[placeholder*="手机号/用户名/邮箱"]',
            'input[name="userName"]',
        ]

        for selector in phone_selectors:
            try:
                phone_input = self.page.locator(selector).first
                if phone_input.count() > 0:
                    phone_input.fill(phone)
                    break
            except:
                pass

        # Enter password immediately (no wait)
        password_inputs = self.page.locator('input[type="password"]').all()
        for pwd_input in password_inputs:
            try:
                if pwd_input.is_visible():
                    pwd_input.fill(password)
                    break
            except:
                pass

    def agree_to_terms_and_submit(self):
        """Agree to terms and immediately click login button."""
        # Find and check checkbox
        checkboxes = self.page.locator('input[type="checkbox"]').all()
        for checkbox in checkboxes:
            if checkbox.is_visible() and not checkbox.is_checked():
                checkbox.check()
                break

        # Immediately click login button (no delay)
        submit_selectors = [
            'button:has-text("登录")',
            'input[type="submit"]',
        ]

        for selector in submit_selectors:
            try:
                submit_btn = self.page.locator(selector).first
                if submit_btn.count() > 0 and submit_btn.is_visible():
                    submit_btn.click()
                    return True
            except:
                pass

        return False

    def handle_verification(self):
        """Handle verification step after login - click 去验证 button."""
        self.page.wait_for_timeout(2000)

        # Look for "去验证" button
        print("正在查找'去验证'按钮...")
        verify_selectors = [
            'text=去验证',
            'button:has-text("去验证")',
            'a:has-text("去验证")',
        ]

        for selector in verify_selectors:
            try:
                verify_btn = self.page.locator(selector).first
                count = verify_btn.count()
                print(f"选择器 '{selector}' 找到 {count} 个元素")

                if count > 0:
                    is_visible = verify_btn.is_visible()
                    print(f"  按钮可见: {is_visible}")

                    if is_visible:
                        verify_btn.click()
                        print("✓ 已点击'去验证'按钮")

                        # Wait for verification code input to appear
                        print("等待验证码输入界面出现...")
                        self.page.wait_for_timeout(3000)

                        # Check if verification input appeared
                        code_input = self.page.locator('input[placeholder*="验证码"]')
                        if code_input.count() > 0:
                            print("✓ 验证码输入界面已出现")
                            return True
                        else:
                            print("验证码输入框未出现，但继续...")
                            return True
            except Exception as e:
                print(f"  错误: {e}")

        print("未找到'去验证'按钮")
        return False

    def wait_for_verification_page_ready(self):
        """Wait for verification page to be ready."""
        print("等待验证码输入界面加载...")

        # Wait up to 10 seconds for verification input to appear
        for i in range(10):
            self.page.wait_for_timeout(1000)

            # Check for verification code input
            code_input = self.page.locator('input[placeholder*="验证码"]')
            if code_input.count() > 0 and code_input.first.is_visible():
                print("✓ 验证码输入框已可见")
                return True

            # Also check for text inputs that might be the code input
            all_inputs = self.page.locator('input[type="text"]').all()
            for inp in all_inputs:
                try:
                    if inp.is_visible():
                        placeholder = inp.get_attribute("placeholder") or ""
                        if '验证' in placeholder:
                            print("✓ 验证码输入框已可见")
                            return True
                except:
                    pass

        print("验证码输入框未出现，但继续...")
        return False

    def get_verification_code_from_user(self):
        """Prompt user to enter verification code using GUI dialog."""
        print("\n" + "="*50)
        print("正在等待用户输入验证码...")
        print("="*50)

        # Try tkinter GUI dialog first
        try:
            import tkinter as tk
            from tkinter import simpledialog

            # Create hidden root window
            root = tk.Tk()
            root.withdraw()
            root.focus_force()

            # Show input dialog
            code = simpledialog.askstring(
                "百度网盘验证码",
                "请查看手机短信，输入收到的验证码：",
                parent=root
            )

            root.destroy()

            if code:
                print(f"收到验证码: {code}")
                return code.strip()
            else:
                print("用户取消了输入")
                return ""

        except Exception as e:
            # Tkinter failed, print instructions and wait
            print(f"GUI弹窗失败: {e}")
            print("请在浏览器窗口中手动输入验证码...")
            print("脚本将继续等待登录完成...")
            return ""

    def enter_verification_code(self, code: str):
        """Enter the verification code into the input field."""
        print(f"正在填写验证码: {code}")

        # Try multiple selectors for verification code input
        code_selectors = [
            'input[placeholder*="验证码"]',
            'input[placeholder*="请输入验证码"]',
            'input[name*="code"]',
            'input[name*="verify"]',
            'input[id*="code"]',
            'input[id*="verify"]',
        ]

        for selector in code_selectors:
            try:
                print(f"尝试选择器: {selector}")
                code_input = self.page.locator(selector).first
                count = code_input.count()
                print(f"  找到 {count} 个元素")

                if count > 0:
                    is_visible = code_input.is_visible()
                    print(f"  可见: {is_visible}")
                    if is_visible:
                        code_input.fill(code)
                        print(f"✓ 验证码已填写")
                        self.page.wait_for_timeout(500)
                        return True
            except Exception as e:
                print(f"  错误: {e}")

        # Fallback: try all visible text inputs
        print("尝试所有可见的文本输入框...")
        all_inputs = self.page.locator('input[type="text"]').all()
        print(f"找到 {len(all_inputs)} 个文本输入框")

        for i, inp in enumerate(all_inputs):
            try:
                if inp.is_visible():
                    placeholder = inp.get_attribute("placeholder") or ""
                    print(f"  输入框 {i}: placeholder='{placeholder}'")

                    if '验证' in placeholder or 'code' in placeholder.lower():
                        inp.fill(code)
                        print(f"✓ 验证码已填写到输入框 {i}")
                        self.page.wait_for_timeout(500)
                        return True
            except Exception as e:
                print(f"  错误: {e}")

        print("未找到验证码输入框")
        return False

    def submit_verification_code(self):
        """Click the submit button after entering verification code."""
        print("正在提交验证码...")

        submit_selectors = [
            'button:has-text("确定")',
            'button:has-text("提交")',
            'button:has-text("验证")',
            'a:has-text("确定")',
            'input[type="submit"]',
        ]

        for selector in submit_selectors:
            try:
                submit_btn = self.page.locator(selector).first
                if submit_btn.count() > 0 and submit_btn.is_visible():
                    submit_btn.click()
                    print("验证码已提交")
                    self.page.wait_for_timeout(2000)
                    return True
            except:
                pass

        return False

    def wait_for_login_after_verification(self, timeout=30):
        """Wait for login to complete after verification."""
        print("等待登录完成...")

        start_time = __import__('time').time()
        while (__import__('time').time() - start_time) < timeout:
            # Check if URL changed (logged in)
            current_url = self.page.url
            if 'disk' in current_url or 'main' in current_url:
                print(f"登录成功! URL: {current_url}")
                return True

            # Check for logout button
            if self.page.locator('text=退出').count() > 0:
                print("登录成功! 发现退出按钮")
                return True

            # Check if no longer on verification page
            if self.page.locator('text=去验证').count() == 0:
                print("验证页面已消失")
                self.page.wait_for_timeout(2000)
                return True

            self.page.wait_for_timeout(500)

        print("等待登录超时")
        return False

    def wait_for_login_success(self):
        """Wait for successful login indication."""
        # Step 1: Click "去验证" button FIRST
        print("===== 步骤1: 点击'去验证'按钮 =====")
        verification_clicked = self.handle_verification()

        if verification_clicked:
            # Step 2: Wait for verification code input page to appear
            print("===== 步骤2: 等待验证码输入界面 =====")
            self.wait_for_verification_page_ready()

            # Step 3: Take screenshot to show current state
            self.page.screenshot(path='/tmp/baidu_verification_page.png')
            print("已保存验证页面截图到 /tmp/baidu_verification_page.png")

            # Step 4: NOW prompt user for verification code (after page is ready)
            print("===== 步骤3: 获取验证码 =====")
            code = self.get_verification_code_from_user()

            if code:
                # Step 5: Enter the verification code
                print(f"===== 步骤4: 填写验证码 {code} =====")
                entered = self.enter_verification_code(code)

                if entered:
                    # Step 6: Submit the verification code
                    print("===== 步骤5: 提交验证码 =====")
                    self.submit_verification_code()
                else:
                    print("未能填写验证码，请手动操作...")

                # Step 7: Wait for login to complete
                print("===== 步骤6: 等待登录完成 =====")
                self.wait_for_login_after_verification(timeout=30)
            else:
                print("未输入验证码，等待手动操作...")
                self.wait_for_login_after_verification(timeout=60)
        else:
            # No verification needed, just wait
            print("无需验证码，等待登录完成...")
            self.page.wait_for_timeout(3000)

        # Take screenshot of final state
        self.page.screenshot(path='/tmp/baidu_final_state.png')
        print(f"===== 最终 URL: {self.page.url} =====")

        return self.page.locator('text=退出').count() > 0

    def login(self, phone: str, password: str):
        """Complete login flow."""
        self.navigate_to_home()
        self.click_login_button()
        self.select_account_login()
        self.enter_credentials(phone, password)
        self.agree_to_terms_and_submit()
        return self.wait_for_login_success()
