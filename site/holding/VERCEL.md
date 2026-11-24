# Vercel deployment

The original zero-JavaScript holding page from commit `be4e5e297acfdb02389be698b4c644d6328bbe09` was uploaded from an isolated, hash-verified snapshot. Concurrent uncommitted language-picker work was preserved and excluded.

## Confirmed deployment

- Project: `kisanmitraa-holding` (created initially as `vercel-preview`, then successfully renamed).
- Team: `atharvavavhal-gmailcoms-projects`.
- Project ID: `prj_xO9xLLTPYGlfQefZTCu87KiBCK8i`.
- Deployment ID: `dpl_CDwXhPTg3zhb98mS2ywiK6pfSBKe`.
- URL: https://vercel-preview-nzkhbt2yr-atharvavavhal-gmailcoms-projects.vercel.app
- Inspector: https://vercel.com/atharvavavhal-gmailcoms-projects/vercel-preview/CDwXhPTg3zhb98mS2ywiK6pfSBKe
- CLI status: `READY`.
- Actual target returned by Vercel: `production`. Vercel automatically selected production for this first deployment even though the command omitted `--prod`.
- No custom domain, DNS, paid setting, analytics, environment variable, or repository integration was configured.

An additional explicit `--target=preview` request returned without a deployment ID or URL. Its completion is unconfirmed; it is not the confirmed release above. Later account inspection and HTTP checks were blocked by DNS resolution errors for api.vercel.com. Inspect the project's deployments before starting another deployment if resolving that preview attempt.

## Configuration

`vercel.json` translates the original Cloudflare headers into Vercel headers, keeps the framework as Other (`null`), skips installation/build, and serves the project directory. The empty Permissions-Policy value is preserved. The CSP intentionally disallows JavaScript, matching the original brief and deployed snapshot.

`.vercelignore` excludes release archives, documentation and Cloudflare's `_headers` file. These source configuration files are recorded in a separate Vercel setup commit; the original implementation commit was not amended.

The upload folder is:

```text
site/holding/dist/be4e5e2/vercel-preview/
```

It contains only the original runtime files, Vercel configuration, and ignored local project-link metadata. No backend/mobile/database/brand source files were uploaded. Project linkage is stored under that folder's `.vercel/project.json`, not at the repository root. The existing repository `dist/` ignore rule excludes this generated directory from Git.

Do not deploy the current working site/holding directory until the separate language-picker work is reviewed: the new Vercel configuration retains the original script-free CSP. Deployments from the isolated directory use the original committed page instead.

For a future explicit preview of the verified snapshot, first check the unresolved preview request in Vercel, then run from the repository root if a new preview is needed:

```sh
vercel deploy site/holding/dist/be4e5e2/vercel-preview --yes --target=preview
```

## Verification

Passed: Vercel accepted and completed the initial deployment; configuration JSON parsed; build/install commands are blank; deployed snapshot file hashes match the original release manifest; no JavaScript is included; original image/assets/local references were checked during packaging.

Not verified live: homepage and custom 404 responses, security/cache response headers (including whether an empty Permissions-Policy field survives), runtime transfer, browser rendering, Lighthouse, or WhatsApp previews. HTTP access via CLI and the web reader did not produce usable responses in this environment. Previous browser/sandbox and font fallback limitations remain. All Marathi still requires native-speaker review.

## Future apex connection

The HTML canonical, sitemap, robots and sharing URLs remain exactly https://kisanmitraa.online/. The custom domain is not connected by this task. Until the domain is connected, the absolute sharing-image URL may be unavailable even though the PNG is present on the deployment.

Connecting the apex, arranging www redirects, and validating HTTPS are separate owner actions. Domain values must be copied from this Vercel project's actual Domains screen; do not reuse Cloudflare-specific DNS instructions from the previous deployment handoff.

References: [Vercel static builds](https://vercel.com/docs/builds/configure-a-build), [Vercel headers](https://vercel.com/docs/project-configuration/vercel-json#headers).
