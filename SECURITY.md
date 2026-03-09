# Security & Operations (for panel / defense)

## Authentication & access

- **Login rate limiting:** Failed login attempts are limited per IP (e.g. 8 per minute) to reduce brute-force risk. Excess attempts return HTTP 429 with a friendly message.
- **Password policy:** When users set or change their password (first login or Change Password), the system enforces:
  - Minimum 8 characters
  - At least one letter and one number
- **Session cookies:** HttpOnly, SameSite=Lax; Secure in production (HTTPS).
- **Security headers:** Responses include `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`.

## Database backup

- **Production (Railway):** Database backups are handled by Railway. In the Railway project dashboard: **Database → Backups**. Automated backups can be enabled/configured there; point-in-time recovery depends on the current Railway plan. No application code is required for backup; it is an infrastructure feature.

## Secrets

- Application secrets (e.g. `SECRET_KEY`, database credentials) are not committed. Use environment variables and `.env` locally; on Railway, set variables in the project **Variables** tab. See `.env.example` for the list of variable names.
