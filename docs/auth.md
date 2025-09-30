# Auth

## Design Overview

### Introduction

This document outlines the authentication mechanism for our website (`frontend.website.com`). The system utilizes the university's official questionnaire platform (`https://wj.sjtu.edu.cn/`) as a proxy for its SSO infrastructure, enabling secure, passwordless authentication. This flow is based on a One-Time Password (OTP) model, providing a robust and user-friendly experience for signup, login, and password recovery within a streamlined single-page application flow.

### Authentication Flow

The process is designed as a linear, redirect-based flow that is compatible across all browsers and WebView environments.

1. **Initiation and Bot Prevention**

   A user on a designated page (e.g., `/signup`) is verified by a Cloudflare Turnstile challenge. Upon success, the frontend sends an `initiate` request to our backend (`api.website.com`), declaring the user's intent (`action`).

2. **OTP Generation and User Redirection**

   The backend validates the Turnstile response, generates a cryptographically secure 8-digit OTP, and associates it with a short-lived (10-minute) `temp_token`. The backend sets this `temp_token` in a secure, `HttpOnly` cookie and returns the OTP and the relevant pre-configured questionnaire URL. (Use different questionnaires for different actions.) The frontend prominently displays the OTP and a copy button. When the user clicks this button, the OTP is copied to their clipboard, frontend shows "Copied!", and they are automatically redirected to the questionnaire URL within the current tab after 1 second (no countdown or displaying remaining seconds). The OTP is also appended to the URL as a `otp_hint` parameter for user convenience.

3. **Identity Assertion via Questionnaire**

   The user is now on the university's questionnaire page. If required, they log in with their university credentials, paste or type the OTP into the form, and submit it.

4. **Callback and State Hand-off**

   The questionnaire platform instantly redirects the user back to our unified callback URL (e.g., `https://frontend.website.com/callback?action=signup&account={{.User}}&answer_id={{.AnswerID}}`), which includes parameters specifying university account, a unique submission ID, and the original intent. The callback page sends this information to our backend for verification. The browser automatically includes the `temp_token` cookie in this request.

5. **Backend Validation**

   The backend performs a rigorous validation, confirming the submission details against the OTP and the `temp_token` (read from the cookie) records stored in Redis. Upon success, the OTP is consumed, and the `temp_token` is marked as verified, now containing the authenticated user's identity.

6. **Flow Completion**

   The backend returns a success response to the callback page. The callback page stores a non-sensitive state object (e.g., `{ status: 'verified', action: 'signup', expires_at: ... }`) in `localStorage` and redirects the user back to the original page they started from (e.g., `/signup`). This page, now detecting the verified flow state in `localStorage`, intelligently renders the next step of the flow (e.g., the password creation form) instead of the initial OTP component.

## Security Analysis

### Overview

This authentication flow is hardened by its stateless, token-based design. It relies on short-lived, single-use credentials and verifiable, server-side intent, which mitigates common web application vulnerabilities.

### Key Security Mechanisms

- **Bot Prevention**: Cloudflare Turnstile gates all authentication initiation points.
- **Cryptographically Secure Tokens**: The OTP and `temp_token` are generated using a CSPRNG.
- **`HttpOnly` Cookie Storage**: The `temp_token` is stored in a secure, `HttpOnly` cookie, preventing access from client-side JavaScript and mitigating XSS-based token theft.
- **Time-Limited Validity**: OTP is valid for 2 minutes; `temp_token` for 10 minutes.
- **One-Time-Use OTP**: The OTP-to-token link is deleted from Redis immediately after use.
- **Hashed Token Storage**: The `temp_token` is stored in Redis using its SHA256 hash as the key (`temp_token_state:<sha256(temp_token)>`).
- **Server-Side Intent Enforcement**: The backend maps each `quest_id` to a specific `action` and enforces this link during verification.

## Implementation Details

### Components & Stack

- **Frontend**: Vue.js (`frontend.website.com`) with Vue Router
- **Backend**: Django / Django REST Framework (`api.website.com`)
- **Cache/State Store**: Redis
- **Bot Prevention**: Cloudflare Turnstile
- **Infrastructure**: Cloudflare in front of Nginx.

### Frontend Architecture (Vue Components)

#### `AuthInitiate.vue` (Reusable Component)

- **Props**: `action` (String: `signup`, `login`, `reset_password`).
- **Logic**:
  1. Checks `localStorage` for a non-expired OTP record. If found, displays it to allow the user to re-copy. Expired OTP and auth flow state records in `localStorage` are cleared.
  2. If no valid OTP exists, renders the Cloudflare Turnstile widget.
  3. On Turnstile success, calls `POST /api/auth/init` endpoint with its `action` prop.
  4. On receiving the `otp` and `redirect_url` (the `temp_token` is set as a cookie by the backend), stores `{ otp, expires_at }` and `{ status: 'pending', expires_at }` in `localStorage` to track the flow's state.
  5. Displays the OTP and copy button. On click, it copies the OTP, provides visual feedback, and initiates the redirect to the URL received from backend.

#### Page-Level Components

##### `Signup.vue` (`/signup`)

On mount, checks `localStorage` for an `auth_flow` state object with `status: 'verified'`, `action: 'signup'`, and a non-expired timestamp.

- **If not found**: Renders `<AuthInitiate action="signup" />`.
- **If found**: Renders `<SetPasswordForm action="signup" />`.

##### `Login.vue` (`/login`)

Redirect to `/` if already logged in. Multiple login methods, including password login and questionnaire login, may be more in the future. Both requires passing Turnstile. Uncareful handling of Turnstile widget may cause conflicts. If questionnaire, render `<AuthInitiate action="login" />`. The flow completes at the callback, which redirects to the homepage directly.

##### `ResetPassword.vue` (`/reset`)

On mount, checks `localStorage` for an `auth_flow` state object with `status: 'verified'`, `action: 'reset_password'`, and a non-expired timestamp.

- **If not found**: Renders `<AuthInitiate action="reset_password" />`.
- **If found**: Renders `<SetPasswordForm action="reset_password" />`.

#### `AuthCallback.vue` (`/callback`)

- **Logic**: A transient component.
  1. On mount, parses `account`, `answer_id`, and `action` from the URL query.
  2. Calls `POST /api/auth/verify` with these parameters. The browser automatically sends the `temp_token` cookie.
  3. On success, receives the flow's `action` and `expires_at` timestamp from the backend and writes a state object `{ status: 'verified', action, expires_at }` to `localStorage`.
  4. Redirects: if `action == 'login'`, redirect to `/`. Otherwise, redirect to `/${action}` (e.g., `/signup`).

#### `SetPasswordForm.vue` (Reusable Component)

- **Props**: `action` (String: `signup`, `reset_password`).
- **Logic**: Renders password fields. (password and re-type-password only. Backend fetches username and other info directly from questionnaire platform.) On submit, it sends the new password to `POST /api/auth/signup` or `POST /api/auth/password` (for password reset) based on action. The browser automatically attaches the `HttpOnly` `temp_token` cookie to the request. The frontend does not handle the token. Delete OTP and the auth flow state from `localStorage` on success and redirect to `/`.

### Detailed Backend Process

#### `POST /api/auth/init`

1. **Input**: Receives the user's intended `action` and the `turnstile_token`.
2. **Validation**: Verifies the `turnstile_token` with Cloudflare's API.
3. **Generation**: Generates a cryptographically secure `otp` and a `temp_token`.
4. **Redis Storage**:
   - Links the `otp` to the raw `temp_token` with a 2-minute expiry.
   - Creates a state record for the `temp_token` (keyed by its SHA256 hash). This record contains its `status` (`pending`) and the user's `action`, and has a 10-minute expiry.
5. **Response**: `200 OK` with the `otp` and `redirect_url`. The backend also sets a secure, `HttpOnly` cookie containing the `temp_token` with a 10-minute expiry.

#### `POST /api/auth/verify`

1. **Input**: Receives the `account`, `answer_id`, and `action` from the callback. The `temp_token` is received via the `HttpOnly` cookie sent by the browser.
2. **Token Pre-Validation**: Extracts the `temp_token` from the cookie. This is the fastest check to reject invalid, expired, or already-used tokens.
   - Looks up the state record in Redis using the SHA256 hash of the `temp_token`.
   - Verifies the status is `pending`. If it's already `verified` or missing, return an error.
3. **Security**: Applies strict rate limiting per _valid_ `temp_token` to prevent brute-force attempts on a single verification flow. Check and set rate limit (or attempts count) in Redis.
4. **API Query**: Fetches recent submissions from the questionnaire platform for the given `account`.
5. **Find Submission**: Locates the specific submission matching the `answer_id`. If not found, returns an error.
6. **Extract Data**: Extracts the `submitted_otp` and the questionnaire's unique ID (`quest_id`) from the submission.
7. ~~**Intent Verification**: Confirms that the `quest_id` from the submission correctly maps to the `action` specified in the request, preventing cross-flow attacks.~~ Not needed, different quesitonnaires use different API, cross-flow attacks are not possible.
8. **OTP & Token Link Validation**:
   - Atomically retrieves the expected `temp_token` associated with the `submitted_otp` and deletes the OTP record to prevent reuse. Use atomic `GETDEL` to prevent race condition.
   - If no token is found for the OTP, or if the retrieved token does not exactly match the `temp_token` from the cookie, the request is invalid. Return `401 Unauthorized`.
9. **State Transition**: Updates the state record's status to `verified` and adds the authenticated user details (e.g., `jaccount`, `ip`, time). The record's TTL is preserved.
10. **Action-Specific Logic**: If the `action` is `login`, the user is now fully authenticated. The backend logs them in and immediately deletes the `temp_token_state` record from Redis.
11. **Response**: `200 OK` with the confirmed `action`, an `expires_at` timestamp for the flow state, and a boolean `is_logged_in` flag. This allows the frontend to safely manage its UI state.

#### `POST /api/auth/signup`

1. **Input**: Receives the new `password`. The `temp_token` is received via the `HttpOnly` cookie.
2. **Token Validation**:
   - Looks up the state record in Redis using the SHA256 hash of the `temp_token` from the cookie.
   - Verifies the record exists and its status is `verified`, and its `action` is `signup`.
3. **Password Complexity Check**: Checks the password against complexity and length rules.
4. **Extract Identity**: Retrieves the `jaccount` and `action` from the state record.
5. **Logic**: Creates a new user account, checking first that the `jaccount` does not already exist.
6. **Session Management**: Logs in the user session.
7. **Cleanup**: Deletes the `temp_token_state` record from Redis and sends an instruction to the browser to clear the `temp_token` cookie (set cookie as already expired).
8. **Response**: `200 OK` with a success message confirming the action was completed.

#### `POST /api/auth/password`

1. **Input**: Receives the new `password`. The `temp_token` is received via the `HttpOnly` cookie.
2. **Token Validation**:
   - Looks up the state record in Redis using the SHA256 hash of the `temp_token` from the cookie.
   - Verifies the record exists and its status is `verified`, and its action is `reset_password`. If not, return `403 Forbidden`.
3. **Password Complexity Check**: Checks the password against complexity and length rules.
4. **Extract Identity**: Retrieves the `jaccount` and `action` from the state record.
5. ~~**Identity Verification**: Verifies the `jaccount` is the same with the account of the current user (identified by session).~~ Forget password will fail this.
6. **Password Update**: updates the password of the authenticated user.
7. **Cleanup**: Deletes the `temp_token_state` record from Redis and sends an instruction to the browser to clear the `temp_token` cookie (set cookie as already expired).
8. **Response**: `200 OK` with a success message confirming the action was completed.
