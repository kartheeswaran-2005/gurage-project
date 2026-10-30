from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("request", lambda r: print("REQ:", r.method, r.url, "Auth:", r.headers.get("authorization")) if "/api/" in r.url else None)
        page.on("response", lambda r: print("RESP:", r.status, r.url) if "/api/" in r.url else None)

        print("1. Login as mechanic...")
        page.goto("http://localhost:5500/login.html")
        page.locator("#email").fill("mechanic@bikecare.com")
        page.locator("#password").fill("Staff@1234")
        with page.expect_navigation():
            page.locator("#btn-submit").click()

        print("Logged in, URL:", page.url)

        print("2. Navigate to /owner/dashboard.html (tampering test)...")
        page.goto("http://localhost:5500/owner/dashboard.html")
        page.wait_for_timeout(3000)
        print("Final URL:", page.url)
        browser.close()

if __name__ == "__main__":
    test()
