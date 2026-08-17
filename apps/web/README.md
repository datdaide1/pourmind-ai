# Frontend

The web experience is the supplied Stitch **Liquid Gold** UI source. Its 19
static B2C and B2B screens are served unchanged from `public/stitch/`; the
minimal Next route layer maps product URLs to those source screens. The API
rewrite remains available for later integration beneath this new UI.

## Run locally

```bash
pnpm install --frozen-lockfile
pnpm dev
```

Open `http://localhost:3000`. The development rewrite in `next.config.ts` forwards `/api/*` to `http://127.0.0.1:8000/api/*`, so start the backend separately.

## Commands

| Command | Purpose |
| --- | --- |
| `pnpm dev` | Start the development server |
| `pnpm lint` | Run ESLint |
| `pnpm build` | Create a production build |
| `pnpm start` | Serve the production build |
| `pnpm exec playwright test` | Run browser tests |

## Screen routes

- `/` — PourMind landing
- `/start`, `/chat`, `/recipe`, `/search`, `/profile`, `/sessions` — B2C
- `/b2b` — Bar Copilot dashboard
- `/b2b/recipes`, `/b2b/guests`, `/b2b/menu`, `/b2b/copilot` — B2B modules
- `public/stitch/DESIGN.md` — imported Liquid Gold design directives

The original frontend app, component library, visual test, and former redesign
prototype were removed. Do not add a second visual system alongside Stitch.

Generated Playwright reports and test results are intentionally excluded from Git.
