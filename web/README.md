# Owner website authentication source

The existing Next.js site now has an Owner sign-in page and protected application-review shell. Browser requests use same-origin route handlers; `AUTH_API_URL` is server-only. Access and refresh credentials are kept in `HttpOnly`, `SameSite=Strict` cookies with `Secure` in production. Mutations require a same-origin request plus a CSRF cookie/header. The server checks the backend session and Admin role before returning private data. Partner decisions require a five-minute, password-verified proof bound to the current Admin session. No public Admin registration or production Owner credential is created.

Copy `.env.example` to `.env.local`, set a local or HTTPS `AUTH_API_URL`, then run from `web/`: `npm install`, `npm run typecheck`, and `npm run build`. Use HTTPS and a trusted host/proxy in production. The website contains a small in-process refresh coordinator; multi-instance and cross-tab refresh races need a shared coordination design and browser testing before production. No real partner data or deployment was used here.

Local verification on 2026-11-27 could not install packages because npm registry HTTPS returned `EACCES`. `npm run typecheck` could not find `tsc`, and `npm run build` could not find `next`. The site is **source-implemented but unbuilt and unverified in a browser**.
