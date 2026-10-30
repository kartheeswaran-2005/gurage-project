from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("http://localhost:5500/login.html")
        page.locator("#email").fill("mechanic@bikecare.com")
        page.locator("#password").fill("Staff@1234")
        with page.expect_navigation():
            page.locator("#btn-submit").click()

        tok = page.evaluate("() => sessionStorage.getItem('bikecare_token')")
        user = page.evaluate("() => sessionStorage.getItem('bikecare_user')")
        print("Token:", tok[:25] if tok else None)
        print("User:", user)

        browser.close()

if __name__ == "__main__":
    test()
