import http.server
import socketserver
import os
from pathlib import Path

PORT = 5500
DIRECTORY = Path(__file__).resolve().parent


class SecurityHeadersHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def end_headers(self):
        # Security headers matching production hosting standards
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        # Development: prevent caching so code changes are always reflected
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob: https:; "
            "connect-src 'self' http://localhost:8000 http://127.0.0.1:8000; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self';"
        )
        super().end_headers()


class ThreadedTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def run():
    with ThreadedTCPServer(("", PORT), SecurityHeadersHandler) as httpd:
        print(f"BikeCare Secure Development Frontend Server running at http://localhost:{PORT}")
        print("Serving security headers: CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down frontend server.")


if __name__ == "__main__":
    run()
