from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:5500/login.html")
    page.evaluate("() => sessionStorage.setItem('foo', 'bar')")
    print("Page 1 sessionStorage foo:", page.evaluate("() => sessionStorage.getItem('foo')"))
    page.goto("http://localhost:5500/owner/dashboard.html")
    print("Page 2 sessionStorage foo after page.goto:", page.evaluate("() => sessionStorage.getItem('foo')"))
    browser.close()
