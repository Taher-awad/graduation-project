# Auth Service Security Strategy

## Approach: Stateless JWT Verification with Short Expirations & Refresh Rotation

### Current Vulnerability
Currently, `/auth` relies on long-lived standard JWTs without granular token revocation. If a student's machine is compromised, the token can be replayed indefinitely until natural expiration.

### Implementation Path
1. **Short-Lived Access Tokens:** Decrease `access_token` lifetime to 15 minutes.
2. **Refresh Tokens (HttpOnly Cookies):** Introduce a `/auth/refresh` endpoint. The refresh token must be stored securely in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie, preventing XSS (Cross-Site Scripting) attacks from stealing the token via React's `localStorage`.
3. **Role-Based Access Control (RBAC) Hardening:** Inject the user's role (STAFF vs STUDENT) deeply into the Redis session claims, not just the client token payload, ensuring a user cannot manually alter their JWT payload to gain STAFF upload privileges.
4. **Rate Limiting:** Protect `/auth/login` and `/auth/register` against brute-force attacks via Redis-backed rate limiting (e.g., maximum 5 failed attempts per minute per IP).
