from playwright.sync_api import sync_playwright

def run_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("console", lambda m: print("CONSOLE:", m.type, m.text))
        page.on("pageerror", lambda e: print("PAGE_ERROR:", e))

        print("Navigating to login page...")
        page.goto("http://localhost:5500/login.html")

        print("Filling credentials...")
        page.locator("#email").fill("owner@bikecare.com")
        page.locator("#password").fill("Owner@1234")

        print("Submitting login form...")
        with page.expect_navigation(timeout=10000):
            page.locator("#btn-submit").click()

        print("Navigated successfully to:", page.url)
        print("Page Title:", page.title())

        page.wait_for_selector("#stat-revenue", timeout=8000)
        print("Revenue text:", page.inner_text("#stat-revenue"))

        # Verify no redirect to login happened
        page.wait_for_timeout(2000)
        print("Final URL (must stay on dashboard):", page.url)
        assert "/owner/dashboard.html" in page.url

        browser.close()
        print("ALL CHECKS PASSED PERFECTLY!")

if __name__ == "__main__":
    run_test()
