# Frontend Guidelines

## Closed-Network Requirement

The frontend is ultimately deployed in a closed network without public internet access. Before adding dependencies, fonts, CDN assets, remote resources, or build-time/runtime network calls, read and follow the [closed-network operating principles](docs/closed-network.md). Any change must remain buildable and operable under those constraints.

Before accepting a package, verify its exact version and complete transitive dependency tree in the closed-network Nexus registry, then perform a clean-cache `npm ci` and build using only that registry. Do not commit Nexus URLs or credentials. shadcn and similar registry-backed CLIs must be run before transfer; commit the generated source so no CLI fetch is required inside the closed network.

## Project Decisions

Read the [frontend decision log](docs/decisions.md) before making architectural, dependency, UI-library, styling, or integration changes. Preserve active decisions, account for superseded decisions, and record new material decisions in that document. The implemented chart v1 and planned v2 are separated in [the chart visualization guide](../docs/chart-visualization.md); [the result-store guide](../docs/result-store.md) is design-only and must not be treated as current behavior.

## Architecture & Component Organization

This Vite 7, React 18, strict-TypeScript SPA has no router or `pages/` layer. `src/App.tsx` composes the app. Put shadcn primitives in `src/components/ui/`, copied AI Elements source in `src/components/ai-elements/`, and feature components in `src/components/chat/`; keep domain tool renderers under `chat/tool-results/`. `hooks/` owns behavior and chat state, `lib/` owns API transports and adapters, `types/` owns contracts, and `src/app/globals.css` owns global tokens.

Keep primitives small and presentational. Containers and hooks coordinate state, streaming, and side effects. Do not add business or fetch logic to UI primitives. `use-agent-chat.ts` is the owner of messages, SSE state, retries, cancellation, editing, and regeneration. It exposes those messages to assistant-ui through `useExternalStoreRuntime`; assistant-ui supplies generic thread, composer, viewport, message, action-bar, and Markdown plumbing, but it is not the message-state owner.

Retain the current split between the two UI libraries: assistant-ui handles generic chat interaction, while the copied AI Elements `chain-of-thought`, `tool`, and `task` components support progress and tool presentation. Do not introduce Vercel AI SDK `ai`, `@ai-sdk/react`, `useChat`, `streamdown`, or the AI SDK streaming protocol. Browser-to-backend transport remains the custom `fetch`/`ReadableStream` SSE implementation in `src/lib/chat-api.ts`.

Recharts is used through the local shadcn chart wrapper for the implemented `bar` and `line` result charts. `ChartBlock` dispatches optional backend `ChartSpec` payloads; unsupported or absent chart shapes must retain the table/result fallback. Pie, Gantt, final-answer chart markers, and result-store pagination are not implemented yet.

## Development & Build Commands

Run from `frontend/`:

```bash
npm install
cp .env.example .env.local
npm run dev       # http://localhost:3000
npm run build     # tsc -b && vite build
npm run lint      # eslint .
npm run preview   # serve dist/ on :3000
```

`npm run build` is the current type-check command. No formatter or automated test script is configured; add configuration and package scripts before requiring either.

## Coding & Styling Conventions

Use PascalCase for component symbols and types, camelCase for functions and values, `useX` for hooks, and kebab-case filenames. Prefer named exports, explicit prop types, `@/` imports, and immutable state updates. Preserve streamed assistant content as ordered message parts.

Style with Tailwind v4 and the semantic CSS variables in `globals.css`; never hardcode component colors or add dark-theme rules. Map new shadcn variables to existing project tokens. Use `cn()` for conditional classes. Preserve the three-pane flex/scroll chain with `min-h-0`, `overflow-hidden`, and `shrink-0` where applicable.

Use `--chart-1` through `--chart-5` only for chart series. Keep shadcn variables mapped to existing namespaced project tokens. The current left sidebar is the custom `app-sidebar.tsx`, not the installed shadcn sidebar; do not mix their provider/layout models without an explicit migration decision.

## Testing & UI Quality

No automated frontend test command is currently configured. When adding tests, prefer Vitest plus React Testing Library for components/hooks and Playwright for critical streaming, editing, and regeneration flows. Until then, require `npm run build`, `npm run lint`, and manual verification at narrow, tablet, and desktop widths. Verify composer submit/cancel, auto-scroll, copy/edit/regenerate actions, retry after connection loss, tool-card expansion, and chart/table fallbacks. Check keyboard operation, focus, labels, contrast, reduced motion, loading/empty/error states, and screen-reader announcements. Avoid unnecessary effects and rerenders; memoize only after measurement and lazy-load genuinely heavy UI.

## API Integration & Error Handling

Keep backend access in `src/lib/chat-api.ts` and `src/lib/knowledge-api.ts`; components must not call providers directly. Keep `src/types/chat.ts` synchronized with `backend/api/schemas.py`, backend service result payloads, and chart specs. The stable event types are `text`, `status`, `tool_call`, `tool_result`, `error`, and `done`.

Assistant messages store ordered `MessagePart[]` rather than one text blob. `src/lib/chat-runtime.ts` must preserve that order when converting to assistant-ui parts; status/progress stays in `metadata.custom`. A `done.data.turn_id` is the backend fork anchor used by edit and regenerate requests through `fork_from_turn_id`. Preserve the anchor and truncated message prefix across retries.

Tool results use domain kinds `database`, `knowledge`, `catalog`, and `simulation`; optional charts are nested in database/simulation payloads. The backend currently registers ten tools. `tool-result-card.tsx` has explicit metadata for eight, while recipe tools reach the catalog renderer through `data.kind`; preserve that safe fallback and add explicit metadata when a tool needs a dedicated label or presentation. Treat backend `agent/sdk_tools.py::TOOL_NAMES` as the canonical tool inventory.

The context inspector currently loads only Skills from `/api/knowledge/skills`; Metadata and Prompt remain local dummy data, and the prompt save control is not persistent. Do not describe those panels as backend-connected until APIs exist. Use `AbortController`, represent loading explicitly, normalize transport/stream failures into user-safe states, preserve retry context, and render `connection-banner.tsx` or a local fallback. Add caching only for stable read data, with explicit invalidation; never cache live SSE responses.
