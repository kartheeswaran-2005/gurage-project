
/*
 * BikeCare authentication guard.
 * Re-check authentication whenever a protected page is restored.
 */

async function checkAuthentication() {
    try {
        const response = await fetch("/api/auth/me", {
            method: "GET",
            credentials: "include",
            cache: "no-store"
        });

        if (!response.ok) {
            window.location.replace("/login.html");
            return;
        }

    } catch (error) {
        console.error("Authentication check failed:", error);
        window.location.replace("/login.html");
    }
}

// Check authentication when the page opens.
checkAuthentication();

// Check again when Back/Forward restores a cached page.
window.addEventListener("pageshow", function () {
    checkAuthentication();
});
