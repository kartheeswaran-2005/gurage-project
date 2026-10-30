import sys
from playwright.sync_api import sync_playwright

def run_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Step 1: Login as Owner
        print("--- Step 1: Owner Login ---")
        page.goto("http://localhost:5500/login.html")
        page.locator("#email").fill("owner@bikecare.com")
        page.locator("#password").fill("Owner@1234")
        with page.expect_navigation():
            page.locator("#btn-submit").click()

        print("Logged in as Owner, current URL:", page.url)
        assert "/owner/dashboard.html" in page.url
        page.wait_for_selector("#stat-revenue")
        print("Owner dashboard loaded successfully with stats!")

        # Step 2: Go to Staff Management and create a staff member
        print("\n--- Step 2: Owner creates staff member with temporary password ---")
        page.goto("http://localhost:5500/owner/staff.html")
        page.wait_for_selector("#btn-open-create-staff", timeout=8000)
        page.locator("#btn-open-create-staff").click()
        page.wait_for_selector("#create-staff-modal.active", timeout=5000)

        import time
        unique_email = f"mechanic_{int(time.time())}@bikecare.com"
        page.locator("#new-staff-email").fill(unique_email)
        page.locator("#new-staff-name").fill("Automated Test Mechanic")
        page.locator("#new-staff-role").select_option("mechanic")
        page.locator("#btn-submit-create").click()

        # Modal with temp password should appear
        page.wait_for_selector("#temp-password-modal.active", timeout=8000)
        temp_pwd = page.locator("#display-temp-password").inner_text().strip()
        print(f"Created staff: {unique_email} with temp password: {temp_pwd}")
        assert len(temp_pwd) >= 16

        # Dismiss modal so it doesn't block background clicks
        page.locator("#btn-ack-temp").click()
        page.wait_for_selector("#temp-password-modal", state="hidden", timeout=5000)

        # Step 3: Logout
        print("\n--- Step 3: Owner logs out ---")
        page.locator(".btn-logout").first.click()
        page.wait_for_url("**/login.html**")
        print("Successfully logged out, URL:", page.url)

        # Step 4: Login with Temporary Password
        print("\n--- Step 4: First login with temporary password ---")
        page.locator("#email").fill(unique_email)
        page.locator("#password").fill(temp_pwd)
        page.locator("#btn-submit").click()

        # Panel 2 should automatically become visible
        page.wait_for_selector("#panel-setup-password", state="visible", timeout=8000)
        print("First-login detected! Switched automatically to 'Choose your new password' panel!")

        # Step 5: Test real-time checklist
        print("\n--- Step 5: Real-time password policy validation ---")
        page.locator("#new-password").fill("GoodPass@2026")
        page.locator("#confirm-password").fill("GoodPass@2026")
        
        # Check that all checklist rules are marked valid
        valid_count = page.locator(".checklist-item.valid").count()
        print(f"Checklist items marked valid: {valid_count}/5")
        assert valid_count == 5

        page.locator("#btn-save-password").click()
        page.wait_for_selector("#login-success", state="visible", timeout=8000)
        print("Password saved successfully message displayed!")

        # Step 6: Login with new permanent password
        print("\n--- Step 6: Login with permanent password ---")
        page.locator("#email").fill(unique_email)
        page.locator("#password").fill("GoodPass@2026")
        with page.expect_navigation():
            page.locator("#btn-submit").click()

        print("Navigated to:", page.url)
        assert "/mechanic/dashboard.html" in page.url
        print("Mechanic dashboard opened successfully without session expiration!")

        # Step 7: URL Tampering Protection
        print("\n--- Step 7: Testing URL Tampering Protection ---")
        # Mechanic tries to manually open Owner Dashboard
        page.goto("http://localhost:5500/owner/dashboard.html")
        page.wait_for_timeout(2000)
        print("After trying to access /owner/dashboard.html, URL is:", page.url)
        # Should be kicked back to /mechanic/dashboard.html with flash alert
        assert "/mechanic/dashboard.html" in page.url
        print("URL Tampering successfully blocked! Redirected back to authorized dashboard!")

        # Step 8: Back / Forward & Logout Protection
        print("\n--- Step 8: Testing Back button protection ---")
        page.locator(".btn-logout").first.click()
        page.wait_for_url("**/login.html**")
        print("Signed out. Now clicking browser Back button...")
        page.go_back()
        page.wait_for_timeout(2000)
        print("After Back button, URL is:", page.url)
        # Auth guard must not allow viewing protected dashboard
        assert "/login.html" in page.url
        print("Back button protection confirmed! Unauthenticated user cannot view cached dashboard!")

        browser.close()
        print("\n=======================================================")
        print("ALL 8 END-TO-END BROWSER CHECKS PASSED WITH 100% SUCCESS!")
        print("=======================================================")

if __name__ == "__main__":
    run_test()
