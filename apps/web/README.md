# Frontend

Next.js App Router client for cocktail chat, catalog search, and menu planning. It renders structured UI blocks received from the backend over SSE.

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

## Structure

- `src/app/`: routes and layouts
- `src/components/chat/`: chat input and messages
- `src/components/sdui/`: typed server-driven UI components
- `src/lib/sseClient.ts`: streaming client
- `tests/`: Playwright specifications

Generated Playwright reports and test results are intentionally excluded from Git.
