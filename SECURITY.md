# BikeCare Security Documentation & Threat Model

## 1. Security Architecture & Threat Model

| Threat / Risk | Mitigating Security Control | Implementation Location | Test Coverage |
| :--- | :--- | :--- | :--- |
| **Credential Guessing / Brute-Force** | Minimum 10 chars, uppercase, lowercase, numbers, common password blacklist, email user part forbidden. 5 failed login limit in 15 mins triggers 15-min lockout (HTTP 429). | `app/core/password_policy.py`, `app/api/auth.py` | `test_password_policy_rules`, `test_brute_force_lockout_after_five_failures` |
| **Account Enumeration** | Timing-safe generic error `"Invalid email or password"` for missing user, bad password, or inactive account. Dummy bcrypt check on non-existent accounts. | `app/api/auth.py`, `app/core/security.py` | `test_login_wrong_password` |
| **Token Theft / Session Hijacking** | Access tokens kept in JavaScript memory (15 min expiry), refresh tokens (7 days) stored hashed (SHA-256) in HttpOnly, SameSite=Lax cookie scoped to `/api/auth`. Token family rotation cancels stolen sessions on reuse. | `app/api/auth.py`, `app/core/security.py`, `frontend/js/api.js` | `test_refresh_token_rotation_and_theft_defense` |
| **Stale Session / Delayed Revocation** | `token_version` on `User` verified on every request. Incremented on password change, role update, deactivation, and logout-all. | `app/core/deps.py`, `app/api/auth.py`, `app/api/staff.py` | `test_staff_forced_password_change`, `test_change_password` |
| **Default Staff Password Exposure** | Owner-created staff receive `must_change_password = True`. All endpoints except `/auth/change-password` and `/auth/logout` return HTTP 403 `PASSWORD_CHANGE_REQUIRED`. | `app/api/staff.py`, `app/core/deps.py`, `frontend/js/auth-guard.js` | `test_staff_forced_password_change` |
| **Account Takeover / Stolen Passwords** | Optional TOTP Two-Factor Authentication (`pyotp`) with AES-encrypted secrets, 8 single-use recovery codes, and rate-limited second-factor challenge. | `app/api/auth.py`, `app/core/security.py` | `test_two_factor_auth_full_lifecycle` |
| **Insecure Direct Object References (IDOR)** | Ownership and provider checks on all object retrieval endpoints (`get_job_for_user`, `get_provider_scope`). Returns HTTP 404 (not 403) to prevent leaking record existence. | `app/core/deps.py`, `app/api/bikes.py`, `app/api/providers.py`, `app/api/estimates.py` | `test_customer_cannot_view_another_customer_bike`, `test_owner_cannot_patch_another_provider`, `test_estimate_calculation_and_approval` |
| **Privilege Escalation / Mass-Assignment** | `model_config = ConfigDict(extra='forbid')` on all Pydantic request models. Prevents injecting `role`, `provider_id`, `status`, or totals. | `app/schemas/*.py` | `test_extra_fields_forbidden_in_schemas` |
| **Unauthenticated Route Exposure** | Automated route test inspects FastAPI routing table and asserts authentication dependency on all routes outside the public allowlist. | `tests/test_security_hardening.py` | `test_all_routes_require_authentication` |
| **SQL Injection (SQLi)** | Parameterized queries exclusively via SQLAlchemy ORM. SQL wildcards (`%`, `_`) sanitized and escaped in search endpoints. | `app/api/providers.py`, `app/api/requests.py` | `test_sql_and_xss_payload_safety` |
| **Cross-Site Scripting (XSS)** | HTML escaping via `escapeHtml()` in frontend templates, `textContent` rendering, and Content Security Policy (CSP) meta headers. | `frontend/js/format.js`, `frontend/*.html`, `app/main.py` | `test_sql_and_xss_payload_safety` |
| **Clickjacking & MIME-Sniffing** | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy`. | `app/main.py` (SecurityHeadersMiddleware), `frontend/serve.py` | `test_security_headers_present_on_api` |
| **Cross-Site Request Forgery (CSRF)** | Custom header `X-Requested-With: BikeCare` required for cookie-based endpoints (`/auth/refresh`, `/auth/logout`) with strict Origin validation. | `app/api/auth.py`, `frontend/js/api.js` | `test_refresh_token_rotation_and_theft_defense` |
| **Price Tampering & Concurrency Race** | Server-side calculation of all financial amounts. Row-level database locking (`with_for_update`) during customer estimate decisions. | `app/services/estimates.py`, `app/services/invoicing.py` | `test_estimate_calculation_and_approval` |
| **Duplicate Payments & Invoice Tampering** | Unique reference constraint per invoice (`uq_payments_invoice_reference`). Payments capped at invoice balance. Invoices immutable: void and reissue required. | `app/models/payment.py`, `app/services/invoicing.py` | `test_duplicate_payment_reference_rejected`, `test_payment_exceeding_balance_rejected` |
| **Malicious File Uploads / Polyglots** | Magic byte validation, extension checks (`.jpg`, `.jpeg`, `.png`, `.webp`, `.pdf`), Pillow image re-encoding (EXIF & GPS stripped), random path naming (`provider_id/job_id/uuid.ext`), 5-min signed URLs. | `app/services/storage.py`, `app/api/files.py` | `test_files_and_assistant.py` |
| **Tamper / Lack of Accountability** | Immutable audit log table (`audit_logs`) with automated password/token redaction. Owner dashboard with date/user/entity filters and CSV export. | `app/models/audit_log.py`, `app/services/audit.py`, `app/api/audit.py`, `frontend/owner/audit.html` | `test_audit_log_captures_actions_without_secrets` |

---

## 2. Authentication & Session Flow

```
1. Customer / Staff Login
   POST /api/auth/login
   ├── Credentials Validated
   ├── Access Token (JWT, 15m) -> Returned in JSON (JavaScript Memory)
   └── Refresh Token (256-bit random) -> Set in HttpOnly, SameSite=Lax Cookie (/api/auth)

2. Authenticated API Call
   GET /api/requests
   └── Headers: { Authorization: "Bearer <access_token>" }
       └── Middleware verifies JWT signature, expiration, and user.token_version

3. Silent Refresh on Access Token Expiry (401)
   POST /api/auth/refresh
   ├── Header: { X-Requested-With: "BikeCare" }
   ├── Cookie: bikecare_refresh
   ├── Validates SHA-256 hash & family_id in refresh_tokens table
   ├── Issues new Access Token (15m) + new Refresh Token (Rotation)
   └── Detects token reuse -> Revokes entire token family immediately!
```

---

## 3. Environment Variables Reference

| Variable | Default (Dev) | Production Requirement | Purpose |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | `development` | `production` | Enables production hardening (HSTS, SSL DB enforcement, disables docs). |
| `DATABASE_URL` | `sqlite:///...` | `postgresql://...sslmode=require` | Database connection string with SSL required in production. |
| `SECRET_KEY` | *(Must be set)* | Random 32+ character key | Signs JWT tokens and derives encryption keys. |
| `ACCESS_TOKEN_MINUTES`| `15` | `15` | Short-lived access token lifespan. |
| `REFRESH_TOKEN_DAYS` | `7` | `7` | Refresh token lifespan. |
| `CORS_ORIGINS` | `http://localhost:5500` | Exact `https://` domain(s) | Allowed browser origins for credentialed CORS. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Exact production domain(s) | TrustedHostMiddleware host whitelist. |
| `ENABLE_2FA` | `false` | `true` | Feature flag for TOTP Two-Factor Authentication. |
| `TOTP_ENCRYPTION_KEY` | *(Derived from SECRET_KEY)* | 32-byte secure key | Encrypts TOTP secrets in database via Fernet. |
| `COOKIE_SECURE` | `false` | `true` | Enforces `Secure` flag on refresh cookies. |
| `RATE_LIMIT_GLOBAL` | `120/minute` | `120/minute` | IP-based global rate limit. |

---

## 4. Production Deployment Checklist

1. [ ] **TLS / HTTPS**: Configure reverse proxy (Nginx, Caddy, or Cloudflare) with valid SSL certificates and HTTP to HTTPS redirection.
2. [ ] **Web Server Headers**: Verify `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and CSP headers are active.
3. [ ] **Least-Privilege Database User**: Create a dedicated application role without superuser or DDL privileges (run migrations under a separate deployment user).
4. [ ] **Secret Rotation**: Rotate `SECRET_KEY` and `TOTP_ENCRYPTION_KEY` using secure key management (e.g. AWS Secrets Manager, Doppler, or HashiCorp Vault).
5. [ ] **Automated Backups**: Configure point-in-time recovery (PITR) and daily automated snapshots for PostgreSQL.
6. [ ] **Log Monitoring & Alerting**: Ingest `audit_logs` into SIEM or log management tools (e.g. Datadog, CloudWatch) with alerts on `LOGIN_LOCKOUT` and `SECURITY_TOKEN_REUSE_DETECTED`.

---

## 5. Known Limitations
- The in-memory rate limiting mechanism (`slowapi`) runs per-process. In a horizontally scaled cluster, configure a Redis backend for shared rate limit counters.
- The optional `scan_file()` hook is stubbed for integration with external antivirus engines (e.g. ClamAV or VirusTotal API).
