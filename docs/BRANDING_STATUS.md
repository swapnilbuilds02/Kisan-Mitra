# Kisan Mitra — Branding Status

**Status:** Branding concerns register.  
**Authoritative brand rules:** `brand/BRAND.md` (logo usage, colours, typeface, asset placement, FORGE endorsement).  
**Rule:** Do not change any logos, colours, or brand assets without owner approval.

---

## 1. Authoritative Brand Assets

| Asset | Location | Status |
|-------|----------|--------|
| Primary logo | `brand/KISAN-MITRA-BRAND/01-Primary-Logo/krushi-mitra-ai-primary.png` (+ sizes, SVG, PDF) | Owner-supplied; installed (BRAND-001/002) |
| Logo variations (light/dark) | `brand/KISAN-MITRA-BRAND/02-Logo-Variations/` | Replaced (BRAND-003) |
| Standalone symbol | `brand/KISAN-MITRA-BRAND/03-Standalone-Symbol/` | Replaced (BRAND-003) |
| App icons & splash | `brand/KISAN-MITRA-BRAND/04-App-Icons/` | Replaced (BRAND-004); packaging unverified |
| Favicons | `brand/KISAN-MITRA-BRAND/05-Favicon/` (+ `site/holding/assets/`) | Replaced (BRAND-003) |
| Brand colours | `brand/KISAN-MITRA-BRAND/07-Brand-Colors/kisan-mitra-colors.css` | Present |
| Brand rules | `brand/BRAND.md` | Authoritative |
| FORGE endorsement | `brand/forge/` | Horizontal SVG; smaller than Kisan Mitra logo |

---

## 2. Unresolved Branding Concerns

### CONC-BRAND-001 — Product name vs artwork [OWNER DECISION DEC-001]

**The conflict:** The supplied primary artwork reads **"Krushi Mitra AI"**. The repository, product copy, PRD, and documentation review all use **"Kisan Mitra"**.

**Implication:** The logo change does not rename the product (per `brand/BRAND.md` §Identity), but the name mismatch blocks final UI copy, domain, app-store listing, and legal text until the owner decides whether to rename the product to "Krushi Mitra AI" or keep "Kisan Mitra" with the artwork as an intentional exception.

**Required:** Owner decision (DEC-001). Do not rename anything in code or docs until approved.

---

### CONC-BRAND-002 — Colour palette contradiction [OPEN]

**The conflict:** `brand/BRAND.md` defines:
- Deep Forest `#174C38` — primary (~75–80% visual weight)
- Agricultural Green `#34785A` — secondary
- Harvest Gold `#C5A451` — accent, under 5%

`docs/product-documentation/04_FRONTEND_SPECIFICATION_KISAN_MITRA.md` §1.1 defines:
- Primary Green `#1B5E20` — primary buttons, header bars
- Harvest Gold `#F57F17` — Pro badges, highlights, CTA

These palettes disagree on the primary colour and accent values.

**Implication:** Frontend design tokens and brand guidelines are inconsistent; a developer cannot determine which colour to implement.

**Required:** Reconcile the palettes into a single authoritative set (prefer `brand/BRAND.md` as the brand source of truth) and update the frontend spec to match. No visual change without owner approval.

---

### CONC-BRAND-003 — App icon packaging unverified [OPEN]

**The conflict:** App icon and splash assets exist (iOS/Android 1024×1024 masters, adaptive foreground/background, dark/transparent splash variants), but no Expo/iOS/Android build exists.

**Implication:** Launcher packaging, adaptive-icon rendering, and splash display on real devices are unverified.

**Required:** Mobile build verification (blocked by ENV-NPM-001 — npm registry inaccessible). Do not change icon assets without owner approval.

---

### CONC-BRAND-004 — Obsolete variant cleanup [VERIFIED — working tree only]

**Status:** 142 obsolete PNG branding variants archived/removed; 57 recovered branding files retained; 40 older design assets retained (per `RECOVERY_WORKSPACE/RECOVERY_REPORT.md` and `TASK_COMPLETION_LOG.md` BRAND-001 to BRAND-004). These changes are in the working tree only; not committed or deployed.

**Required:** Preserve recovery evidence (`RECOVERY_WORKSPACE/`). Do not `git add .` while recovery evidence is inside the repo. Stage specific approved branding paths only when Git write access is restored.

---

## 3. What Must Not Change Without Owner Approval

- Logo artwork (any folder under `brand/KISAN-MITRA-BRAND/`)
- Primary logo file selection or placement
- Brand colour hex values
- Typeface (Inter)
- FORGE endorsement usage or prominence
- Product name in copy, domain, or app-store metadata

## 4. Related Documents

| Document | Purpose |
|----------|---------|
| `brand/BRAND.md` | Authoritative brand rules (logo, colours, typeface, asset placement) |
| `brand/KISAN-MITRA-BRAND/` | All brand asset folders |
| `docs/product-documentation/04_FRONTEND_SPECIFICATION_KISAN_MITRA.md` §1.1 | Frontend colour palette (contradicts brand guidelines — see CONC-BRAND-002) |
| `docs/DECISION_LOG.md` | DEC-001 (product name), pending |
| `docs/KNOWN_ISSUES.md` | ISS-BRAND-001 to ISS-BRAND-003 |
| `RECOVERY_WORKSPACE/RECOVERY_REPORT.md` | Branding recovery evidence |
