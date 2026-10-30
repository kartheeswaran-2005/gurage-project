from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("response", lambda r: print("RESP STATUS:", r.status, r.url) if r.status >= 400 else None)
        page.on("requestfailed", lambda r: print("FAILED REQ:", r.url, r.failure))

        page.goto("http://localhost:5500/login.html")
        page.locator("#email").fill("mechanic@bikecare.com")
        page.locator("#password").fill("Staff@1234")
        with page.expect_navigation():
            page.locator("#btn-submit").click()

        print("Navigating to owner dashboard...")
        page.goto("http://localhost:5500/owner/dashboard.html")
        page.wait_for_timeout(3000)
        browser.close()

if __name__ == "__main__":
    test()
