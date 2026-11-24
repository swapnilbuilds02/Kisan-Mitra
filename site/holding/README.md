# Kisan Mitra holding page

Static, unreleased-product holding page for **https://kisanmitraa.online/** (two a's). No service is available yet. Plain HTML and one CSS file; no JavaScript, framework, build, form, analytics, or remote resources.

## Local preview

From the repository root:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory site/holding
```

Open http://127.0.0.1:8765/ and http://127.0.0.1:8765/404.html. Python's server does not apply `_headers` and its generic missing-path error is not this custom 404. Cloudflare Pages applies the headers and serves the top-level `404.html` for missing paths.

## Content and brand

Edit the page text and bilingual SEO metadata in `index.html`. Marathi strings are separate elements. The requested error-page text lives in `404.html`. Both pages use the same CSS. All Marathi strings need review by a native speaker before publication.

Logos and favicons are unmodified copies from `brand/`. The PDF restricts Agricultural Green to the logo's four datum bars and secondary UI states, so the decorative ruler uses ivory hairlines and exactly one small gold notch. Green is used on the development-status border. The ruler appears at widths of 1024px and above to keep narrow layouts uncluttered. The intended page-surface ratio is 80% forest / 20% ivory, using 4:1 grid rows with natural document scrolling.

Font retrieval with `npm pack @fontsource/inter @fontsource/noto-sans-devanagari` failed: `ENOTFOUND registry.npmjs.org`. No font binaries are shipped. The specified offline stack is used: Inter, Noto Sans Devanagari, Kohinoor Devanagari, Devanagari Sangam MN, Mukta, system-ui, sans-serif. Rendering therefore depends on installed fonts. See `assets/fonts/README.md` before adding self-hosted subsets.

The contact block is commented out. Replace the placeholder only when a verified address or number is supplied. There is no live contact link or personal-data collection.

Assets have one-year immutable caching as requested. When replacing an asset, give it a new filename and update its references to avoid stale caches.

## Cloudflare Pages (manual steps only; nothing deployed)

1. After review and merge, create a Pages project connected to this repository. Choose the production branch deliberately (normally `main`).
2. Select no framework preset. Keep the repository root as the root directory. Leave the build command empty: this site requires no build command or dependency installation. Set the build output directory to **`site/holding`**. Cloudflare's static-HTML guide currently suggests the optional no-op `exit 0`; this project follows the requested empty build command.
3. Review the generated `pages.dev` preview, custom 404, security response headers, sharing image, and mobile rendering before adding a domain.
4. Under the Pages project's Custom domains, add **`kisanmitraa.online`** and follow Cloudflare's domain-verification instructions. Use the exact two-a spelling.
5. Add `www.kisanmitraa.online` as a custom domain if needed for its certificate. In the zone's redirect rules, redirect hostname `www.kisanmitraa.online` permanently (301) to `https://kisanmitraa.online`, preserving the path and query string. Verify both HTTP and HTTPS www URLs reach the apex in one canonical redirect.
6. Enable **Always Use HTTPS** in the zone's SSL/TLS settings and verify the apex certificate is active. Test HTTP-to-HTTPS and www-to-apex redirects.
7. Confirm the deployed CSP matches `_headers`, `robots.txt` and `sitemap.xml` use the apex, and the absolute OG image URL returns a 1200×630 PNG. Verify WhatsApp's preview after publication; metadata and image fetching cannot be checked against the unconfigured domain locally.

References: [Cloudflare static HTML](https://developers.cloudflare.com/pages/framework-guides/deploy-anything/), [custom domains](https://developers.cloudflare.com/pages/configuration/custom-domains/), [headers](https://developers.cloudflare.com/pages/configuration/headers/), [www to apex](https://developers.cloudflare.com/pages/how-to/www-redirect/), [Permissions Policy syntax](https://www.w3.org/TR/permissions-policy/).

## Verification status in this environment

- Structural HTML checks, local resource references, image alt text and dimensions, one H1 per document, JSON/XML parsing, logo byte identity, no scripts/inline styles/event handlers, and computed text contrast: passed.
- Formal HTML validation: **not run**; html-validate is unavailable and not cached.
- Python preview: attempted; socket binding was denied by the sandbox.
- Playwright screenshots at 320, 375, 414, 768, 1024, and 1440; visual glyph/FORGE inspection; runtime network bytes; CSS-disabled rendering; 200% zoom; horizontal-overflow and layout-shift measurements: **not run** because Chrome cannot start in the sandbox. No screenshots were produced.
- Lighthouse mobile: **not run**; Lighthouse is unavailable and not cached. No scores are claimed.
- Installation outside the sandbox was rejected by automatic approval review because escalated permissions are disabled.
- A throwaway Chromium OG template and browser verification script are prepared in `/tmp/km-holding-tools/`; they are not part of the site or commit. Run `node /tmp/km-holding-tools/verify.cjs` with the preview server running in a Chromium-capable environment. The script creates the sharing PNG and screenshots under `/tmp/km-holding-shots/`. Visual inspection is still necessary.

| Text or mark | Background | Contrast |
| --- | --- | ---: |
| Warm Ivory #F7F7F2 | Deep Forest #174C38 | 9.19:1 |
| Muted ivory (78% ivory, approximately #C6D1C9) | Deep Forest #174C38 | 6.28:1 |
| Deep Charcoal #202923 | Warm Ivory #F7F7F2 | 13.93:1 |
| White #FFFFFF (official reverse logo) | Deep Forest #174C38 | 9.87:1 |
| #17140F (official FORGE logo) | Warm Ivory #F7F7F2 | 17.09:1 |

All text pairs meet WCAG AA for normal text. The empty `Permissions-Policy:` field expresses the requested empty policy, rather than the invalid bare `()` dictionary. Hosting handling of an empty field still requires verification. The green status border and faint ruler hairlines are decorative, not information-bearing controls. The gold notch is decorative and never text. No plate rectangle exists in the FORGE SVG, but its final browser appearance remains unverified.

## Sharing image and inspection

With explicit user approval, `assets/og-image.png` was rendered with macOS AppKit/CoreText instead of Chromium, which cannot start under the current sandbox. The image is 1200×630, 25,728 bytes after lossless PNG compression, with an exact #174C38 background, the unmodified reverse SVG rasterized on it, and the headline read from `index.html`. It uses the local Kohinoor Devanagari Bold face, with zero missing glyph IDs. The complete image was visually inspected: the headline is unclipped and the logo has generous clear space. This approved renderer substitution is a deviation from the original Chromium requirement.

A native AppKit/CoreText inspection was performed separately from browser QA. `/tmp/km-holding-tools/native-inspection.png` was visually inspected: the official FORGE SVG has no plate box on Warm Ivory, and the sample “द्राक्ष · विश्वासू” has readable conjuncts with no missing-glyph boxes. CoreText reported zero missing glyph IDs and used Kohinoor Devanagari. This does not establish browser rendering or cross-platform font availability.

Static analysis finds no third-party request sources, scripts, inline styles, or event handlers. The source-byte estimate for the HTML, CSS, two logos, favicon SVG, and manifest is 13,829 bytes before HTTP headers. This is an estimate, not a network measurement. All shipped HTML/CSS, icons, metadata files, and the PNG together are 52,415 raw bytes (excluding documentation); no font binaries are shipped. This is below both transfer budgets before HTTP headers, but runtime network transfer is unmeasured. The PNG contains 20 exact Harvest Gold pixels (0.00265%); including antialiasing its logo-notch bounding box remains below 0.01% of the image. Full-page pixel coverage is unmeasured; the desktop motif notch occupies only 36 square CSS pixels, plus approximately 22 square pixels of gold in the 200px logo. This is well below 5% by vector geometry. The SVG contains exactly one gold motif notch; gold is not assigned to any text, and the official logos are unchanged.

## Assumptions and decisions

- The directory will be served at the domain root, so local URLs start with `/`.
- The canonical hostname is exactly `kisanmitraa.online`; www redirects will be configured manually by the owner later.
- The year remains the supplied static 2026; no JavaScript updates it.
- No contact details are available. Placeholder links exist only inside an HTML comment.
- The explicit 404-page requirement is an exception to the instruction to keep all copy in `index.html`; all holding-page copy is in `index.html`, and error-page copy is in `404.html`.
- The user explicitly approved native CoreText rendering for the sharing image after Chromium was blocked.
- The specified offline font fallback is permitted after the failed npm attempt. No downloaded fonts, font loading shifts, CDN links, or font requests are introduced. General layout-shift behavior is unverified.
- Muted ivory is Warm Ivory at 78% opacity over Deep Forest. It is not an additional brand swatch.
- The 80/20 forest/ivory split refers to the document's intended surfaces. The explicitly requested all-forest sharing-image background is separate.
- The decorative ruler is hidden below 1024px. At narrow widths the facts wrap naturally; they are not a horizontally scrolling row.
- Logo whitespace includes the SVG's own canvas and the header's external padding. Width is 160px on mobile and 200px from 768px; the FORGE endorsement is 100px. The official Kisan logo's symbol is about 34.6px high at 200px logo width, so its required 17.3px clear space is provided by the canvas plus surrounding spacing.
- “Empty Permissions-Policy” means an empty field value, not a bare `()` value. The latter is not a valid structured dictionary. The deployment must verify how its host handles the empty field.
- No framework, build, publication, domain purchase/configuration, external messaging, or Git push is authorized or performed. Tooling and inspection files exist only under `/tmp`, outside the shipped directory.

## Marathi needing native-speaker review

Review all visible Marathi, the metadata, and accessible labels, including:

- `किसान मित्र — द्राक्ष उत्पादकांसाठी | Kisan Mitra`
- `विकासाधीन`
- `तुमच्या द्राक्षबागेचा विश्वासू साथी`
- `छाटणीच्या तारखेपासून दिवसागणिक पिकाचे वेळापत्रक, मराठीत. किसान मित्र अजून तयार होत आहे आणि अद्याप उपलब्ध नाही.`
- `मराठीत`, `द्राक्ष उत्पादकांसाठी`, `महाराष्ट्र`
- `द्राक्ष उत्पादकांसाठी मराठीत पिकाचे वेळापत्रक. किसान मित्र विकासाधीन आहे; अद्याप उपलब्ध नाही.`
- `तुमच्या द्राक्षबागेचा विश्वासू साथी. किसान मित्र अजून तयार होत आहे आणि अद्याप उपलब्ध नाही.`
- `किसान मित्र`, `किसान मित्र — मुख्य पान`, `उत्पादनाविषयी`
- `पान सापडले नाही`, `मुख्य पानावर जा`

## Push commands

```sh
cd /Users/atharva/KM/Kisan-Mitra
git switch feat/holding-page
git push -u origin feat/holding-page
```

The requested single commit uses `feat(site): add kisanmitraa.online holding page`. No push has been made.

## File inventory

Sizes are raw bytes, not runtime transfer measurements. Documentation is not loaded by the page.

| File (relative to site/holding) | Bytes |
| --- | ---: |
| `404.html` | 1297 |
| `README.md` | 12924 |
| `_headers` | 332 |
| `assets/favicon-180x180.png` | 2676 |
| `assets/favicon-192x192.png` | 2750 |
| `assets/favicon-512x512.png` | 5194 |
| `assets/favicon.ico` | 375 |
| `assets/favicon.svg` | 962 |
| `assets/fonts/README.md` | 325 |
| `assets/forge-horizontal.svg` | 1365 |
| `assets/kisan-mitra-reverse.svg` | 2395 |
| `assets/og-image.png` | 25728 |
| `index.html` | 5145 |
| `robots.txt` | 72 |
| `site.webmanifest` | 390 |
| `sitemap.xml` | 162 |
| `styles.css` | 3572 |
