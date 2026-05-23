# Playwright 测试开发工作流

## 核心原则
- E2E测试覆盖关键用户路径，非全量覆盖
- 每个测试独立，无顺序依赖
- 失败截图+日志自动留存

## 标准流程
```bash
pip install playwright
playwright install chromium  # 安装浏览器

# 运行测试
pytest tests/ -v --headed    # 有头（调试）
pytest tests/ -v             # 无头（CI）
```

## 常用API
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    page.goto("https://example.com")
    page.click("#submit-btn")
    assert "Success" in page.content()
    
    # 截图
    page.screenshot(path="failure.png")
    browser.close()
```

## 页面对象模型
```python
class LoginPage:
    def __init__(self, page):
        self.page = page
        self.username = page.locator("#username")
        self.password = page.locator("#password")
        self.submit = page.locator("button[type=submit]")
    
    def login(self, user, pwd):
        self.username.fill(user)
        self.password.fill(pwd)
        self.submit.click()
```

## 调试技巧
- `page.pause()` 打开Playwright检查器
- `record_video` 录制操作过程
- `console` 捕获JS错误

## 在Hermes中的使用
- 配合`dogfood` skill做Web应用QA
- 截图用`page.screenshot()` → vision分析
- 等待用`wait_for_selector`而非固定sleep
