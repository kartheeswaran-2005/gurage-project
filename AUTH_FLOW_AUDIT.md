# BikeCare: Authentication Flow, Browser Navigation & URL Protection Audit

## Executive Summary
This document conducts a comprehensive audit of the current authentication, navigation, and URL protection implementation across the BikeCare backend (FastAPI + SQLAlchemy) and frontend (Vanilla HTML/CSS/JS). It details existing mechanisms, identifies gaps and security vulnerabilities relative to the target requirements, and defines the remediation roadmap.

---

## 1. Database & User Model

### Current Implementation
- `User` model (`backend/app/models/user.py`) has:
  - `must_change_password: bool` (default `False`).
  - `token_version: int` (default `1`).
  - MFA / TOTP columns (`two_factor_enabled`, `totp_secret_encrypted`, `recovery_codes_hash`).

### Gaps & What is Wrong/Missing
1. **Missing Expiry & Timestamp Tracking**:
   - `temp_password_expires_at` (`datetime`, nullable) is missing.
   - `password_changed_at` (`datetime`, nullable) is missing.
   - Temporary passwords currently never expire, presenting a lingering credential compromise risk.
2. **Database Migration**:
   - An Alembic migration is required to add `temp_password_expires_at` and `password_changed_at` to the `users` table without destroying existing production/test data.

---

## 2. Staff Account Creation & Password Reset

### Current Implementation (`backend/app/api/staff.py`)
- `POST /api/staff` allows an optional `initial_password` supplied in request payload. If absent, generates a 12-character password.
- Sets `must_change_password = True` and returns `temporary_password` in `StaffCreateResponse`.
- `update_staff` supports role change and activation toggle.

### Gaps & What is Wrong/Missing
1. **Password Generation & Expiry**:
   - Requirement dictates a cryptographically random **16-character temporary password** using Python's `secrets` module (never custom user input).
   - Temporary password must expire in **72 hours** (`temp_password_expires_at = now + 72 hours`).
   - Plaintext password must never be logged or persisted in plain text.
2. **Owner Reset Password Endpoint Missing**:
   - `POST /api/staff/{id}/reset-password` does not exist.
   - Requirement: An owner (same provider only) can reset a staff member's password, generating a new temporary password, setting `must_change_password = True`, setting expiry to 72 hours, invalidating current sessions, incrementing `token_version`, logging an audit event, and returning the temporary password once. Owner cannot reset their own password via this endpoint.
3. **Owner Creation CLI & Seed Script**:
   - `python -m app.create_owner` currently prompts for a permanent password and sets `must_change_password = False` by default. It must create the owner with `must_change_password = True`.
   - `python -m app.seed_demo` should respect `DEMO_SKIP_FORCE_PASSWORD_CHANGE=true`.
   - Dedicated CLI command `python -m app.reset_password <email>` for owner password reset is missing.

---

## 3. Login Flow & Initial Password Selection

### Current Implementation (`backend/app/api/auth.py` & `frontend/login.html`)
- On `POST /api/auth/login`, if user credentials are valid and `must_change_password == True`:
  - The server currently issues a regular `access_token` and an `HttpOnly` refresh cookie!
  - `deps.py` partially blocks other endpoints with `403 PASSWORD_CHANGE_REQUIRED`, but the session cookie and JWT are already issued.
  - In frontend, `login.html` attempts to redirect the user to `/change-password.html`.

### Gaps & What is Wrong/Missing
1. **Security Vulnerability (Premature Session Issuance)**:
   - When `must_change_password == True`, the server **must NOT issue an access token or set a refresh cookie**.
   - Instead, the server must return `{status: "PASSWORD_CHANGE_REQUIRED", setup_token: "<signed_token>"}` where `setup_token` is valid for only 10 minutes and restricted exclusively to `POST /api/auth/set-initial-password`.
   - If the temporary password has expired (> 72 hours), the login endpoint must reject authentication with: `"Temporary password expired. Ask the owner to reset it."`
2. **Initial Password Endpoint Missing**:
   - `POST /api/auth/set-initial-password` does not exist.
   - Endpoint must accept `{setup_token, new_password, confirm_password}`.
   - Must enforce the strict password policy (minimum 10 characters, uppercase, lowercase, digit, not common, not containing user's email prefix).
   - Must reject if `new_password` equals the temporary password.
   - Must update password hash, set `must_change_password = False`, set `password_changed_at`, increment `token_version`, revoke all refresh sessions, write an audit event, and return success without automatically logging in.
3. **Defense in Depth**:
   - If any API request reaches `get_current_user` with a normal access token for a user where `must_change_password == True`, immediately return 403 `PASSWORD_CHANGE_REQUIRED`.
4. **Single-Page UX in `login.html`**:
   - `login.html` currently redirects away to `change-password.html`.
   - Requirement: Two in-page panels within `login.html` (no navigation so `setup_token` resides only in JS memory):
     - Login Panel.
     - "Choose your new password" Panel (with new password, confirm password, show/hide toggle, live criteria checklist).
     - Upon successful submission, returns to login panel with: *"Password saved. Please log in with your new password."*

---

## 4. Back / Forward Navigation & Session Lifecycle

### Current Implementation (`frontend/js/api.js`, `frontend/js/auth-guard.js`)
- `auth-guard.js` runs only on `DOMContentLoaded`.
- It does not listen to `pageshow` (or `event.persisted` from bfcache) or `visibilitychange`.
- There is no hide-until-verified styling (`html.auth-pending body { display: none; }`), allowing protected UI elements to flash before redirects execute.
- `login.html` does not check or terminate existing sessions upon navigation.
- If a user logs out or clicks Back to `login.html`, pressing Forward or navigating back to a dashboard can display stale cached content.

### Gaps & What is Wrong/Missing
1. **Automatic Sign-Out on Login Page**:
   - When `login.html` is displayed (initial load, Back, Forward, typed URL, or restored via bfcache `pageshow`) and a session exists:
     - Must call `POST /api/auth/logout`.
     - Revoke refresh token in database and delete the cookie.
     - Clear in-memory tokens.
     - Broadcast logout to other tabs.
     - Display notice: *"You were signed out. Please log in."* (Do not display notice on fresh first-time visit).
   - Must respect config flag `STRICT_BACK_LOGOUT` in `frontend/js/config.js` (default `true`).
2. **Session Status Endpoint (`GET /api/auth/session`)**:
   - Currently, checking session requires calling `/api/auth/refresh` (which rotates tokens and can cause race conditions or unnecessary database writes).
   - Missing dedicated endpoint `GET /api/auth/session` that checks the `bikecare_refresh` cookie validity and returns `{authenticated: bool, role: string|null}` **without rotating or extending the token**.
3. **Forward after Back Guard**:
   - When Forward is pressed, the dashboard guard runs immediately. Finding no session, it must call `location.replace('/login.html?reason=login')`.
   - Dashboard content must never be visible during this check.
4. **Logout Button Behavior**:
   - Logout button must call `/api/auth/logout`, clear all state, and call `location.replace('/login.html?reason=loggedout')`. Back/Forward must never reveal protected content.
5. **Hide-until-verified**:
   - Every protected page must include `class="auth-pending"` on the `<html>` root tag, and `html.auth-pending body { display: none !important; }`.
   - The guard removes `auth-pending` only after session and role are cryptographically verified with the server.
6. **Cache Headers**:
   - `frontend/serve.py` must send `Cache-Control: no-store, no-cache, must-revalidate` for all HTML/JS.
   - Backend API authenticated responses must enforce `Cache-Control: no-store`.
7. **Session Expiry & Inactivity Timeout**:
   - Refresh cookie must be a session cookie (`max_age=None`).
   - Absolute lifetime: 8 hours (`SESSION_MAX_HOURS`).
   - Inactivity timeout: 15 minutes (`IDLE_TIMEOUT_MINUTES`), warning dialog at 14 minutes with "Stay signed in" button, automatic logout at 15 minutes.
8. **Multi-Tab Sync**:
   - Broadcast channel `BroadcastChannel('bikecare-auth')` (with `localStorage` event fallback) so logout in one tab synchronizes across all open tabs.
9. **Single Dashboard with In-Page Module Switching**:
   - In each role's dashboard (`dashboard.html`), sidebar clicks must change modules using `history.replaceState(null, '', '#module-name')` so module clicks never create history entries. Back button from dashboard immediately returns to `login.html`.

---

## 5. Route Protection & URL Tampering

### Current Implementation
- Role checks in frontend are rudimentary (inspecting `pathname.includes('/owner/')`).
- No central route definition or route-denied auditing endpoint.
- If an employee tries to open `/owner/dashboard.html`, they are redirected without server-side audit logging.

### Gaps & What is Wrong/Missing
1. **Single Source of Truth (`frontend/js/routes.js`)**:
   - Map roles to dashboard:
     - `customer`: `/customer/dashboard.html`
     - `employee`: `/employee/dashboard.html`
     - `mechanic`: `/mechanic/dashboard.html`
     - `owner`: `/owner/dashboard.html`
   - Define public pages and role module permissions.
2. **Route Tampering & Audit Logging**:
   - If a logged-in user changes the address bar to another role's dashboard:
     - Store flash message in `sessionStorage`: *"You do not have access to that page."*
     - Send fire-and-forget `POST /api/security/route-denied` with `{path: location.pathname}`.
     - Backend writes audit log event and rate-limits the endpoint.
     - `location.replace(HOME[user.role])` immediately.
3. **404 Handling**:
   - Unknown URLs must render a clean `404.html`.
   - `serve.py` must fall back to `404.html` for unknown paths.
4. **Open Redirect Protection**:
   - If `?next=` is used, only accept values from the allowlist of the user's role dashboards; ignore anything else.
5. **Backend Defense-in-Depth Matrix**:
   - Pytest matrix verifying every API route rejects other roles with 403 or 404.

---

## 6. Implementation Action Plan
1. **Database & Alembic Migration**: Add `temp_password_expires_at` and `password_changed_at` to `users`.
2. **Backend Auth & Staff Endpoints**:
   - Implement `POST /api/staff` 16-char generation and 72-hour expiry.
   - Implement `POST /api/staff/{id}/reset-password`.
   - Update `POST /api/auth/login` to return `{status: 'PASSWORD_CHANGE_REQUIRED', setup_token}` without cookie/token.
   - Implement `POST /api/auth/set-initial-password`.
   - Implement `GET /api/auth/session` (non-rotating status check).
   - Implement `POST /api/security/route-denied` (with audit logging and rate limiting).
   - Update `app/create_owner.py`, `app/seed_demo.py`, and create `app/reset_password.py`.
3. **Frontend Architecture & Guards**:
   - Create `frontend/js/config.js` (`STRICT_BACK_LOGOUT = true`).
   - Create `frontend/js/routes.js`.
   - Refactor `frontend/js/auth-guard.js` (hide-until-verified, bfcache `pageshow`, visibility re-check, route tampering reporting).
   - Update `frontend/login.html` (dual panels, bfcache logout detection, session broadcast).
   - Update dashboards (`owner`, `employee`, `mechanic`, `customer`) with single dashboard architecture, module switching via `history.replaceState`, `auth-pending` class, idle timeout warning, and BroadcastChannel.
   - Create `frontend/404.html` and update `frontend/serve.py` (no-store headers and 404 fallback).
4. **Testing & Verification**:
   - Pytest unit and integration test suite covering all backend scenarios.
   - Playwright end-to-end browser test suite (Chromium & Firefox) covering all 14 scenarios in Section F.
