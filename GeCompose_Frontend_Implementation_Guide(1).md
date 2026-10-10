# GeCompose — Frontend Design, Motion, Authentication & Backend Integration Guide

**AI implementation brief | Version 1.0 | 10 October 2026**  
**Visual reference:** https://ui.shadcn.com/examples/dashboard  
**Source-of-truth backend reference:** `BACKEND_GUIDE(1).md` (uploaded separately)

> **Instruction to the coding agent:** Treat this as a build specification, not a mood board. Implement a complete, accessible, working interface with real backend integration. Study the existing repository before editing it. Preserve the supplied Python scheduling logic, its approval checks, the independent verifier, and the backend's safety boundaries. Do not invent API endpoints, solver states, approval results, users, schedules, metrics, or chains of custody. Features marked **NEW** require implementation; features marked **EXISTING** map to functions named in the backend guide.

---

## 0. Objective and scope

Rebuild GeCompose as a clean, cohesive, shadcn/ui-style scheduling and constraint-resolution application. The visual experience should feel like a polished enterprise SaaS product: neutral, editorial, lightweight, responsive, thoughtfully animated, and operationally trustworthy. Add beautiful but restrained login and sign-up pages, seamless route/tab changes, animated metric and result cards, a quiet ambient background effect, and genuine progress/feedback states.

**Long-term product:** A universal constraint-and-scheduling conflict solver for education, conferences, seminars, festivals, organizations, government meetings, and other events. **Immediate implementation:** preserve and successfully demonstrate the narrower college-timetable backend provided. Do not imply domain-general functionality is already implemented. Use domain-neutral frontend labels where possible, and phase generalized workspace/constraint entities in later (Section 15).

### Deliverables

1. React + TypeScript web app using the existing shadcn/ui visual language.
2. Clean public auth pages: sign in, sign up, forgot/reset password, and session handling.
3. Authenticated application shell with responsive, collapsible sidebar and working routes.
4. Dashboard, Intake, Review Rules/Constraints, Schedule, Conflicts, Approvals, Publish & Verify, Scoreboard/Analytics, and Chain/Audit Log.
5. Shared motion design system, animated cards and tabs, and a very subtle ambient background.
6. Thin, documented HTTP API over the existing Python `backend/api.py` functions (**NEW**), plus genuine authentication/authorization (**NEW**).
7. Typed frontend API client, loading/error states, tested integrations, accessible keyboard behavior, and dark mode.
8. Developer README, environment example, tests, and a working mock-mode demo.

### Explicit non-goals for this pass

- Rewriting the CP-SAT solver, Gemma prompts, Foundry contract, or hash/checker logic.
- Claiming real government-grade security/compliance, multi-tenancy, SSO, or public-chain approval based on the provided Anvil demo.
- Adding Three.js purely for decoration; make any 3D effect optional and off by default.
- Fabricating percent-complete values for synchronous operations.
- Implementing drag-to-reschedule before the backend supports manual placements and validation.

---

## 1. Non-negotiable backend invariants

From `BACKEND_GUIDE(1).md`, sections 2, 8–12:

- Gemma extracts **draft** rules and writes human explanations; it **does not assign slots**. Only OR-Tools CP-SAT generates schedules.
- A human reviews and confirms rules. AI does not choose the true rule owner, sign approvals, or see private keys.
- `solve()` returns `feasible`, `infeasible`, `unknown`, or `error`; these statuses must remain distinct in the UI.
- `checker.check()` must report no violations before publication; a provisional candidate is not a published timetable.
- Only appropriate cryptographic hashes are written on-chain. Do not put names, audio, images, availability, or full schedules on-chain.
- The existing app uses Anvil **pre-unlocked demo accounts**, not actual user wallets or browser signing. Explain the difference to users.
- Generated spreadsheet parser code executes in the Docker sandbox. Keep the existing mock-mode restrictions.
- The current backend is **one project, one coordinator, four rule types, five weekdays, six one-hour slots per day**. The facade exposes Python functions; it does **not** expose authenticated web endpoints.
- The reference backend is **untested** according to its own guide. Run the named tests and repair genuine integration failures before accepting frontend results.

**Rule ownership warning:** `edit_rule(rule_id, ..., owner=...)` appears in the backend facade. Once a rule is registered on-chain, changing its owner in the database could contradict the immutable on-chain owner. Lock owner edits for confirmed/registered rules until a properly authorized owner-migration design is implemented. Never trust an editable `as_user` string as production proof of authorization.

---

## 2. Recommended architecture

### Frontend stack

- **React + TypeScript + Vite** (or adapt the existing React stack if already established; avoid destructive resets).
- **Tailwind CSS + shadcn/ui** primitives (`Card`, `Button`, `Badge`, `Sidebar`, `Tabs`, `Table/DataTable`, `Sheet`, `Dialog`, `Progress`, `Skeleton`, `Tooltip`, `Form`, `Input`, `Select`, `Sonner/Toast`, `DropdownMenu`, `Avatar`, `Separator`).
- **Lucide React** icons; thin, consistent 16–18px stroke style.
- **Motion for React** (`motion/react`) for enter/exit, stagger and shared layout animation.
- **React Router** for nested public/authenticated routes; keep the app shell mounted while content changes.
- **TanStack Query** for server state, invalidation, deduplication, retries and loading flags.
- **React Hook Form + Zod** for auth and editable rule forms.
- **Recharts** for compact analytics; respect reduced-motion preferences.
- TypeScript types generated from FastAPI OpenAPI where practical; otherwise maintain strictly validated request/response types.

### Backend integration

- **Existing:** Python 3.11+, `backend/api.py` facade, SQLite registry, Gemma clients, Docker sandbox, OR-Tools, Web3/Foundry/Anvil.
- **NEW:** FastAPI routes that call `backend/api.py` without replicating domain logic. Use Pydantic response models, centralized error translation and per-route permission checks.
- **NEW:** authentication service, session persistence, authorization middleware, user and (later) organization data.
- **NEW later:** job persistence / SSE or WebSocket events for long-running solve and intake tasks.

**Important architectural choice:** The provided backend guide mentions Streamlit, and even states that Node.js is not needed for its original implementation. A shadcn/ui React frontend is a **deliberate replacement of that original frontend approach** and therefore adds a Node-based frontend toolchain. This does not require rewriting the Python domain services.

Suggested structure:

```text
frontend/
  src/
    app/
      router.tsx                 # public + authenticated routes
      providers.tsx              # auth, query, theme, reduced motion
      AppShell.tsx               # sidebar + topbar + page content
    components/
      ui/                        # shadcn-generated components
      layout/                    # Sidebar, PageHeader, WorkspaceSwitcher
      motion/                    # PageTransition, AnimatedCard, MotionTokens
      background/                # AmbientBackground (CSS first)
      feedback/                  # OperationProgress, ErrorState, EmptyState
      scheduling/                # ScheduleGrid, SessionCard, RuleCard
      auth/                      # AuthShell, AuthForm, AuthGuard
    features/
      auth/ dashboard/ intake/ rules/ schedule/ conflicts/
      approvals/ publish/ scoreboard/ chain/
    lib/
      api-client.ts
      query-keys.ts
      formatters.ts
      auth.ts
      motion.ts
    styles/globals.css
    types/api.ts
  .env.example
  package.json
backend/
  api.py                        # EXISTING Python facade, preserve signatures
  http/                       # NEW web adapter package
    app.py
    routes/                   # auth, dashboard, intake, rules, solve, etc.
    auth.py
    security.py
    dependencies.py
    schemas.py
```

Inspect actual repository files first and reconcile this blueprint with what exists. Do not create duplicate sources of truth.

---

## 3. Visual system: faithful to the shadcn/ui dashboard

### Layout and density

- White page, subtle neutral surfaces, light gray dividers, minimal decorative surfaces.
- Left sidebar, ~250–260px expanded, collapsible to icon rail (~60–72px). Fixed/sticky on desktop; mobile becomes a sheet/drawer.
- Topbar approximately 56–64px high, with breadcrumb/page title on the left and context actions/profile/theme on the right.
- Content width scales to viewport; use readable `max-width` for auth forms and prose, but let charts/tables use available width.
- Main horizontal padding 24px desktop, 16px tablet/mobile. 24px between major sections, 12–16px card gaps.
- Cards: 1px neutral border, 10–12px radius, 16–24px padding, flat/no shadow. Hover should never look like a floating marketing card.
- Buttons: 32–36px height, normal text case, consistent 6–8px icon gaps.
- Full-width loading and error states should retain the page structure to prevent jumpiness.

### Palette

| Token | Light | Dark | Intended use |
|---|---|---|---|
| `background` | `#FFFFFF` | `#09090B` | Page |
| `foreground` | `#0A0A0A` | `#FAFAFA` | Main text |
| `surface` | `#FFFFFF` | `#111113` | Cards/panels |
| `muted` | `#F9FAFB` | `#18181B` | Low emphasis |
| `muted-foreground` | `#737373` | `#A1A1AA` | Secondary labels |
| `border` | `#E5E5E5` | `#27272A` | 1px lines |
| `accent-blue` | `#2563EB` | `#60A5FA` | Selection, progress, focus |
| `success` | semantic green | semantic green | Confirmed/verified |
| `warning` | semantic amber | semantic amber | Pending/unknown |
| `danger` | semantic red | semantic red | Infeasible/failed/tampered |

Implement actual theme mapping through shadcn CSS variables and Tailwind utilities, not scattered hard-coded values. Blue is the single interaction accent; green/amber/red are status-only. Preserve contrast in dark mode. **No gradients or heavy shadows on application cards.**

### Typography

- Font: Geist or Inter, system fallback.
- Page heading: 20–24px / semibold.
- Card headings: 13px / muted medium.
- KPI numbers: 24–30px / semibold-bold, tabular numerals.
- Section headings: 16–18px / semibold.
- Body and nav: 13–14px.
- Metadata: 12–13px.
- Use sentence case. Avoid uppercase headings and over-dense dashboards.

### Screen components

- Four KPI cards in the first row; no fake performance deltas if no historical data exists.
- A main chart or schedule preview in a restrained bordered panel.
- Dense but legible table with small status badges, filters, pagination and actions.
- Contextual drawers for rule/session details rather than huge modal stacks.
- Consistent empty states, inline field errors, skeletons and toasts.

---

## 4. Motion design: seamless, light and deterministic

**Direction:** Quiet, premium, Linear/Vercel-like motion that helps the user maintain spatial context. Animate actual changes; never animate to hide loading or to give fake progress.

| Component / transition | Duration | Method | Notes |
|---|---:|---|---|
| Hover/background feedback | 100–150ms | CSS transition | No bounce |
| Press feedback | 90–120ms | Scale to `0.985` (optional) | Respect reduced motion |
| Tooltip/dropdown | 150–180ms | Opacity + translateY 4px | Radix accessibility preserved |
| Tab selection | 180–240ms | Shared `layoutId` underline/pill | Keyboard-operable |
| Page content navigation | 180–240ms | Fade + translateY 6px | Sidebar stays mounted |
| Card enter | 260–320ms | Fade + translateY 8px | Stagger 40–55ms max |
| Drawer | 200–250ms | Slide 12–18px + opacity | Keep focus management |
| Sidebar expand/collapse | 200–250ms | Width transition + label fade | Icons do not jump |
| Schedule placement change | 280–450ms | Layout motion | Only genuinely moved sessions |
| Charts | 400–600ms | Controlled reveal | Do not replay on every tab switch |
| Spinner -> verified icon | 180–240ms | Crossfade | Only on confirmed success |

**Implementation rules**

1. Centralize timings/easings in `lib/motion.ts`; use variants rather than ad-hoc effects.
2. Use `AnimatePresence` with stable keys for route-level exits. Use `layoutId` only when element identities really match.
3. Do **not** remount the sidebar, header or persistent charts whenever the route changes.
4. Avoid re-running card entrances on every refetch or text change. Enter once on initial data appearance.
5. Favor `opacity` and `transform`; avoid expensive shadow/filter/layout animation across many rows.
6. Avoid giant page wipes, parallax on content, confetti, exaggerated zoom or bouncing spring presets.
7. Respect `prefers-reduced-motion`: disable background drift and nonessential transitions, preserve clear instant feedback.
8. Animation cannot be a prerequisite for understanding state; status text/icons must be readable without motion.

### React page transition pattern

```tsx
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useLocation, Outlet } from "react-router-dom";

export function AnimatedOutlet() {
  const location = useLocation();
  const reduce = useReducedMotion();
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={location.pathname}
        initial={reduce ? false : { opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={reduce ? undefined : { opacity: 0, y: -4 }}
        transition={{ duration: reduce ? 0 : 0.2, ease: "easeOut" }}
      >
        <Outlet />
      </motion.div>
    </AnimatePresence>
  );
}
```

*Adapt this pattern to the chosen router's nested route implementation. Preserve route data and keyboard focus; do not use animation wrappers to swallow navigation errors.*

### Reusable animated card pattern

```tsx
import { motion, useReducedMotion } from "motion/react";

export function AnimatedCard({ children, delay = 0 }: {
  children: React.ReactNode;
  delay?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0 : 0.28, delay: reduce ? 0 : delay, ease: "easeOut" }}
      className="rounded-xl border border-border bg-card p-5"
    >
      {children}
    </motion.div>
  );
}
```

Only apply staggering to small groups such as four metric cards, not hundreds of table rows.

---

## 5. Ambient background: chill, aesthetic, nearly invisible

**Default implementation: CSS, not Three.js.** The background should read as a premium texture when the page is idle and essentially disappear when the user concentrates on data.

- Use a very faint static dot/grid texture, with an optional slowly drifting low-opacity blue haze **behind** the content, not behind table text.
- Do not apply noticeable gradients to cards. If using a subtle blurred radial layer as ambience, isolate it to the page canvas/auth illustration region.
- Opacity target: ~2–5% grid/dots; ~3–7% blurred accent. This is a qualitative target; verify real contrast visually.
- Drift speed: 20–40 seconds per cycle, translate at most 12–24px; **never** rotate or follow the cursor.
- Never intercept clicks: `pointer-events: none`, `aria-hidden="true"`, proper z-index.
- Pause or omit animation on `prefers-reduced-motion`, background tabs, narrow/mobile layouts, and low-power devices where possible.
- No particle storms, moving stars, laser grids, bouncing orbs, auto-playing videos or constant 3D renders.

Example CSS foundation (tune against both themes):

```css
.ambient-canvas {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}
.ambient-canvas::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image: radial-gradient(currentColor 0.6px, transparent 0.6px);
  background-size: 26px 26px;
  opacity: 0.025;
}
.ambient-orb {
  position: absolute;
  right: -100px;
  top: 14%;
  width: 360px;
  height: 360px;
  border-radius: 9999px;
  background: rgba(37, 99, 235, 0.035);
  filter: blur(85px);
  animation: ambient-drift 30s ease-in-out infinite alternate;
}
@keyframes ambient-drift {
  from { transform: translate3d(0, 0, 0); }
  to { transform: translate3d(-18px, 12px, 0); }
}
@media (prefers-reduced-motion: reduce) {
  .ambient-orb { animation: none !important; }
}
```

Place the `.ambient-canvas` behind an otherwise opaque/legible app shell. If visual QA reveals little or no added value, turn it off in data-dense pages and retain it only for authentication and empty states.

### Three.js decision gate

Do **not** introduce Three.js initially. Consider it only if a later design calls for a meaningful visualization (e.g., an interactive resource-dependency graph) that is inadequately served by SVG/Canvas. If approved, dynamically import it, cap device pixel ratio, pause when hidden, and provide CSS fallback. Decorative 3D has no priority over correctness or speed.

---

## 6. Authentication UX (NEW)

**The provided backend does not implement sign-in/sign-up, sessions, user models or secure app-level ownership. Build these capabilities; do not fake them via localStorage or a front-end-only guard.**

### Routes

| Route | Purpose | UI requirements |
|---|---|---|
| `/auth/sign-in` | Email/password sign in | Email, password, show/hide, forgot password, submit, sign-up link |
| `/auth/sign-up` | Create account | Name, email, password, confirm password (or passwordless flow if backend supports), terms if applicable |
| `/auth/forgot-password` | Request reset | Email input, generic non-enumerating success message |
| `/auth/reset-password` | Apply token | Validated reset token, new password, confirmation |
| `/auth/verify-email` | Optional email verification | Only show if verification delivery is implemented |
| `/app/*` | Authenticated application | Server-backed session validation and access control |

Terminology: **Sign in** = login to an existing account; **Sign up** = register a new account. Do not create two confusing pages named Login and Signin.

### Auth page visual specification

- Background: white/off-white with extremely faint motion texture. Center an auth container, maximum width ~390–440px.
- Desktop: single centered card or carefully restrained split layout; mobile: single column with generous edge padding.
- Top: small GeCompose glyph/logotype, title ("Welcome back" / "Create your account"), one-line supportive subtitle.
- Form: labeled inputs, 40–44px height for comfortable touch targets, clear focus rings, field-level errors.
- Primary submit: near-black button, full width, 40–44px tall. Secondary navigation uses text links.
- Password visibility icon must have an accessible label.
- Validation appears on blur/submit; do not aggressively flag fields before interaction.
- Loading: replace button text with compact spinner while preserving button width and disabled state.
- Invalid credentials: neutral, generic error; never reveal whether a specific email exists.
- Completion: short crossfade and navigate; do not use confetti or heroic fullscreen animations.
- Optional provider buttons (Google/Microsoft) appear **only** if actually configured end-to-end.

### Secure auth implementation (server-backed)

- Prefer opaque server-side sessions stored in **HttpOnly, Secure, SameSite** cookies (Secure in HTTPS production; local development handling explicit). Do not put session JWTs, refresh tokens or passwords into `localStorage`.
- Use CSRF protection for state-changing cookie-authenticated endpoints, with origin checks and a proper token strategy. SameSite is defense-in-depth, not a complete CSRF replacement.
- Use Argon2id for password hashing; never save plaintext passwords or log secrets.
- Rate-limit registration, sign-in and reset flows; generic reset responses, expiry and single-use reset tokens.
- Rotate/invalidate sessions when appropriate; logout invalidates server session, not just a cookie.
- Restrict CORS origins and credential policy; preferably use a same-origin reverse proxy (`/api` -> FastAPI) for the SPA.
- Require server-side authorization on **every** application endpoint; React protected routes are usability only.
- Keep demo-Anvil identities separate from authenticated app users. Selecting `as_user="Dept Head"` in a demo is not proof of blockchain signing authority.

### Auth API contract to implement (NEW)

```text
POST /api/v1/auth/sign-up             {name,email,password} -> 201 user summary
POST /api/v1/auth/sign-in             {email,password} -> 200 user summary + Set-Cookie
GET  /api/v1/auth/me                  -> 200 {id,name,email,roles,...} or 401
POST /api/v1/auth/sign-out            -> 204 + session invalidation
POST /api/v1/auth/forgot-password     {email} -> generic 200
POST /api/v1/auth/reset-password      {token,new_password} -> 204
```

Use server-side validation on all fields. E-mail delivery and reset tokens need real infrastructure; if unavailable in local demo, clearly label the reset flow unavailable rather than pretending to send email. Avoid inventing social-login success states.

### Roles and permissions

Initial demo roles: `admin/coordinator`, `reviewer`, `viewer`. **NEW**, requires persistence and backend enforcement. Protected operations include rule confirmation, rule editing, approvals, publish, and chain details. **Never** equate UI role with on-chain rule ownership; the latter requires separate authorization proof.

---

## 7. Information architecture and route map

```text
/auth/sign-in
/auth/sign-up
/auth/forgot-password
/auth/reset-password
/app/dashboard
/app/intake
/app/rules                 # label: Constraints / Review rules
/app/schedule
/app/conflicts
/app/approvals
/app/publish
/app/scoreboard
/app/chain-log
/app/settings              # account/theme/system status
/app/workspaces/new        # FUTURE/PHASE 2 unless model is implemented
```

### Persistent shell

- Sidebar order: Dashboard, Intake, Constraints, Schedule, Conflicts, Approvals, Publish & verify, Scoreboard, Chain log.
- Bottom: Settings, Help, user avatar menu, compact system health (Gemma intake, Gemma reasoning, sandbox, Anvil; contract status in details).
- Topbar: page title and breadcrumb, optional workspace selector (disabled or labeled demo in v1), contextual primary action.
- Keep sidebar and topbar mounted across route transitions; animate only the main content.
- Active nav highlight must follow actual router location, not a local fake selected value.

### Dashboard (`/app/dashboard`)

Four adaptive cards:

1. Confirmed constraints/rules (from list rules)
2. Active conflict status/count (from latest solve state; show **Not checked** if no run)
3. Scheduled sessions (from existing published schedule or latest feasible pending result)
4. Published schedule version (from actual persisted schedule)

Below: workflow progress; small schedule preview; recent chain events. Avoid fake revenue-style metrics and invented month-over-month deltas.

**Motion:** metric cards appear once with ~50ms stagger; updated values may smoothly count over ~400ms; loading uses card-matched skeletons.

### Intake (`/app/intake`)

Tabs: Text, Audio, Image, Spreadsheet. Provide upload zones, previews, upload safety messaging, and clear call-to-action. Inputs map to actual `ingest_*()` functions. For each accepted input, render returned **draft** rule cards with evidence and a Review action. Use the backend `cache_hit`, `attempts`, `tokens_used`, `seconds` for spreadsheets; do not invent them. If `AUDIO_MODE=transcript`, communicate the fallback.

### Constraints / Review rules (`/app/rules`)

Use a shadcn DataTable with status tabs, search and consistent columns: ID, Rule, Source, Owner, Status, Actions. Row click opens a right-side Sheet with schema-driven params, owner, evidence and actions. Confirm calls real backend registration and only then displays green success. Rejected drafts remain inspectable. `confirmed` owner cannot silently change (see §1).

### Schedule (`/app/schedule`)

Current backend: five weekday columns, six time slots: `09:00`, `10:00`, `11:00`, `12:00`, `14:00`, `15:00`; all sessions occupy one slot. Show teacher/room filters, version, actions, and placements. "Why this slot?" invokes `why_cell(session_id)` after successful scheduling. Only session IDs in `SolveResult.moved` should animate their placement changes; otherwise keep the grid stable. Do not expose fake drag-to-schedule.

### Solve interaction (header/action)

- Disable repeated Solve clicks during a request.
- Show **indeterminate** progress if using current synchronous `solve()`. Text can say "Preparing constraints / Solving / Checking" only if these stages are explicitly observable, otherwise "Generating and validating schedule".
- `feasible`: display schedule and measured `solve_ms`, `moved` and pending publication CTA.
- `infeasible`: show Conflict screen CTA and the returned core rule IDs/owners.
- `unknown`: no result proved in configured time; allow retry/adjust parameters.
- `error`: inline friendly error and no publication CTA.

### Conflicts (`/app/conflicts`)

Provide a calm "Conflict Studio": left issue list, center affected rules/schedule context, right proposed resolutions. Explanation only comes from `explain_conflict()` and options are shown as feasible only when `verified===true` from backend. Option cards display rule, description, approver and a Request approval action. No verified option -> offer manual rule review. Do not let user bypass maximum relaxation cycles.

### Approvals (`/app/approvals`)

Show explicit two-step process: **Approve option** (`approve_option`) then **Apply option** (`apply_option`). Anvil demo must clearly label the chosen pre-unlocked account as a **demo identity**, not a personal authenticated wallet. Handle non-owner rejection, chain downtime, pending receipt and double-submission. After applying, offer Re-solve.

### Publish & verify (`/app/publish`)

Publish only the valid pending schedule via `publish()`. Once server confirms, show hash, transaction hash, version, actual JSON/CSV/ICS exports. Verification accepts a JSON file, calls `verify_file()`, and separately displays `match`, `anchored`, recomputed hash and error. Optional "Tamper-test a copy" changes only a temporary copy, never the original. No celebratory fake "on chain" animation before receipt.

### Scoreboard (`/app/scoreboard`)

Run `run_scoreboard(runs=...)`. Render measured baseline vs GeCompose violations as a small bar chart and result table. In mock mode use the label **Recorded fixture**. If a baseline run produces zero violations, display zero, not a marketing claim.

### Chain log (`/app/chain-log`)

Render real `chain_events()`: `RuleRegistered`, `RelaxationApproved`, `ScheduleAnchored`. Display event, block, hashes where available, expandable raw payload, and Copy action. No invented events.

---

## 8. HTTP adapter: map UI to existing Python facade

**EXISTING:** the reference guide's `backend/api.py` defines Python functions, not routes. **NEW:** implement an HTTP transport layer. Keep the existing function names/signatures internally and do not introduce direct browser access to Gemma servers, Docker, private files, SQLite, Anvil RPC, or Python source.

### Endpoint matrix (proposal; implement and document it)

| HTTP method | Path | Calls / source | Notes |
|---|---|---|---|
| GET | `/api/v1/health` | `api.health()` | Limited public status, detail authenticated |
| GET | `/api/v1/roster` | `api.get_roster()` | Authenticated |
| POST | `/api/v1/intake/text` | `api.ingest_text(text)` | JSON `{text}` |
| POST | `/api/v1/intake/audio` | `api.ingest_audio(bytes, filename)` | `multipart/form-data`, WAV |
| POST | `/api/v1/intake/image` | `api.ingest_image(bytes, filename)` | multipart; validate type/size |
| POST | `/api/v1/intake/sheet` | `api.ingest_sheet(bytes, filename)` | XLSX; return cache metrics |
| GET | `/api/v1/rules?status=` | `api.list_rules(status)` | Draft/confirmed/rejected |
| PATCH | `/api/v1/rules/{id}` | `api.edit_rule(id,params,owner)` | Permission + validation |
| POST | `/api/v1/rules/{id}/confirm` | `api.confirm_rule(id)` | Chain registration; mutation |
| POST | `/api/v1/rules/{id}/reject` | `api.reject_rule(id)` | Mutation |
| GET | `/api/v1/uploads/{filename}` | `api.get_upload(filename)` | Permission + safe filename handling |
| POST | `/api/v1/solve` | `api.solve(minimal_change)` | Return actual `SolveResult` |
| POST | `/api/v1/conflicts/explain` | `api.explain_conflict(conflict)` | `Conflict` request model |
| POST | `/api/v1/options/{id}/approve` | `api.approve_option(id,as_user)` | Demo only unless signer proof exists |
| POST | `/api/v1/options/{id}/apply` | `api.apply_option(id)` | Requires chain approval |
| GET | `/api/v1/schedule/why/{session_id}` | `api.why_cell(session_id)` | Relevant confirmed rules |
| POST | `/api/v1/publish` | `api.publish()` | Never publish invalid pending schedule |
| POST | `/api/v1/verify` | `api.verify_file(bytes)` | JSON file or byte payload |
| POST | `/api/v1/scoreboard` | `api.run_scoreboard(runs)` | Measured results |
| GET | `/api/v1/chain/events` | `api.chain_events()` | Authenticated/audited |

**Needed adapter additions:**

- `GET /api/v1/schedules/latest`: retrieve persisted published schedule metadata and placements. Existing registry has `latest_schedule()`; a new read-only facade wrapper is appropriate.
- `GET /api/v1/schedules/pending` (or job-result lookup): current `solve()` only stores its last feasible result *in memory*. Make pending state session/workspace-scoped and durable if multiple users or server restarts matter. Initially constrain the demo to single coordinator and clearly communicate restart behavior.
- `GET /api/v1/dashboard/summary`: aggregate actual roster, rules, published schedule and most recent solve state, or build the view from existing read calls.
- Idempotency and duplicate-request protection for confirm, approve and publish, where practical.
- Auth endpoints from Section 6, new database tables and authenticated request dependencies.

### Request/response examples

```http
POST /api/v1/intake/text
Content-Type: application/json

{"text":"Prof. Rao cannot teach Monday morning."}
```

Returns an array of `Rule` models with `status="draft"`, `evidence`, `type`, `owner`, `params` and `id`.

```http
POST /api/v1/solve
Content-Type: application/json

{"minimal_change":true}
```

Response shape mirrors `SolveResult`:

```json
{
  "status": "infeasible",
  "schedule": null,
  "conflict": {"rule_ids": ["R1", "R2", "R3"], "owners": ["Dept Head", "Dean", "Prof. Rao"]},
  "moved": [],
  "solve_ms": 43,
  "message": ""
}
```

*This JSON is an example of the schema, not a promised execution result or timing.*

### FastAPI minimal adaptation pattern

```python
# backend/http/app.py — illustrative; align exact imports and middleware with the repo
from fastapi import FastAPI, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from backend import api as domain_api
from backend.http.auth import require_user  # NEW; must really be implemented

app = FastAPI(title="GeCompose API", version="1.0")

class SolveRequest(BaseModel):
    minimal_change: bool = True

@app.post("/api/v1/solve")
async def solve_route(body: SolveRequest, user=Depends(require_user)):
    # NEW: enforce user's coordinator permission and active workspace.
    # EXISTING: keep the CP-SAT/checker logic in domain_api.solve().
    result = await run_in_threadpool(domain_api.solve, body.minimal_change)
    return result
```

Do not blindly paste this example as a complete server. Implement `require_user`, error handling, CORS/CSRF, route permissions, concurrency locking, file limits, session persistence, logging and OpenAPI schemas before describing it as production-ready.

### Client-side API conventions

```ts
const BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    ...init,
    headers: {
      ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init.headers,
    },
  });
  if (!res.ok) {
    // Decode backend's standardized error envelope here.
    throw new Error(`Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
```

**Security note:** add the chosen CSRF token/header handling for cookie-authenticated mutations. Do not set multipart `Content-Type` manually. For `PublishResult.json_bytes/csv_bytes/ics_bytes`, Python byte fields might serialize as strings unexpectedly; define explicit file download endpoints or a documented base64/Blob contract and test byte-perfect roundtrips. For long operations, do not leave an unhandled browser timeout.

---

## 9. Reliable progress and operation lifecycle

### Stage A: current synchronous backend (implement now)

Use shadcn `Progress` in indeterminate presentation (or an accessible custom progress bar/spinner) for `ingest_*`, `solve`, `explain_conflict`, `approve_option`, `publish` and `verify_file`. Display a truthful operation name, short explanatory text and elapsed time optionally. Never fabricate percentages, deterministic steps or successful stages.

For `SolveResult` render exact status. For `IngestSheetResult` render actual `cache_hit`, `attempts`, `tokens_used`, `seconds`. For `PublishResult`, show transaction metadata only after success.

### Stage B: persistent jobs (NEW, recommended for growth)

Add endpoints such as:

```text
POST /api/v1/jobs/solve         -> 202 {job_id,status:"queued"}
GET  /api/v1/jobs/{job_id}      -> {status,phase,elapsed_ms,result?,error?}
GET  /api/v1/jobs/{job_id}/events  -> SSE, optional
POST /api/v1/jobs/{job_id}/cancel -> cancellation request if supported
```

Valid statuses: `queued`, `running`, `completed`, `failed`, `cancel_requested`, `cancelled`; phases represent actual instrumentation. Ensure a single active mutation/solve per demo workspace or use snapshotting/version checks. Persist results, respect server restarts, and prevent cross-user leakage. If precise progress is unavailable, keep the bar indeterminate; lifecycle steps may still be shown truthfully.

---

## 10. State, caching and correctness rules

- Query keys: `['health']`, `['roster']`, `['rules', filter]`, `['latest-schedule']`, `['solve-result', jobId]`, `['chain-events']`, `['scoreboard', runId]`, `['auth','me']`.
- Mutations invalidate relevant caches after success: intake → rules; confirm/reject/edit → rules; solve → schedule/result; approve/apply → rules/conflicts/chain events; publish → latest schedule/chain events/dashboard.
- Avoid stale success: if a prior solve was feasible and current constraints changed, mark the pending result outdated and block publication until re-solve.
- Browser navigation during a long mutation should not silently lose the result; use job status in Phase B or a persistent in-app request manager in Phase A.
- Respect `unknown` versus `infeasible` and empty core cases. Show alternatives only when solver has verified them.
- Use real data to populate every KPI and chart. On absent data, render `—`, `Not checked`, `No schedule yet` or a contextual empty state.
- Upload: validate MIME/signature where possible, extensions, size limits, count limits and safe filenames on the server; avoid exposing raw uploaded assets across users.
- Render server error messages as plain text; never execute them as HTML.

---

## 11. Accessibility, responsiveness and performance

- WCAG-oriented keyboard support: tab order, visible focus ring, Escape to dismiss, labels, ARIA live announcements for async completion/errors, dialogs that trap/restore focus, and semantic tables.
- On mobile: sidebar becomes a drawer; KPI grid becomes 2 columns and then 1; large tables horizontally scroll with clear affordance; schedule grid can switch to agenda/list view.
- Use the same motion strategy for light and dark modes; low-contrast decorative animation must never reduce legibility.
- Prefer CSS/transform animation; avoid repaint-heavy perpetual blur on weak devices. Disable the ambient orb on mobile if it degrades performance.
- Lazy-load substantial routes (Scoreboard, Chain log) and chart libraries; do not block first paint on data unrelated to the current screen.
- Tune for stable layout (reserve skeleton/card dimensions), avoid layout shift, virtualize genuinely huge tables, and debounce expensive search appropriately.
- Reduced-motion must disable ambient drift and nonessential movement, but **not** remove loading/status text.

---

## 12. Error taxonomy and UX copy

| Backend/condition | User-facing behavior |
|---|---|
| Gemma unavailable | “AI intake is unavailable. Try text input or the supported demo fallback.” |
| Audio input unsupported | Show configured transcript/typed fallback; never claim transcription occurred |
| Sandbox down | “Spreadsheet processing is unavailable.” Do not run unsafe parser locally unless allowed mock mode |
| Anvil contract missing after restart | “Approval network needs reinitialization.” Disable approval/publication |
| Non-owner approval | “Approval rejected: this account is not the rule owner.” |
| Solver infeasible | “No schedule satisfies all confirmed constraints.” Link to conflicts |
| Solver unknown | “No conclusive result within the time limit.” Allow retry |
| Independent checker violation | “Schedule validation failed. Publication is blocked.” |
| Verify mismatch | “File integrity could not be verified against the anchored schedule.” |
| Unauthorized | Redirect to sign-in or show “Access denied” (403); never silently fake authorization |
| Empty dataset | Intentional empty state with next action, not placeholder fake metrics |

Keep error tones factual and calm, with human-readable recovery actions. Maintain backend technical detail in development logs, never raw tracebacks in user UI.

---

## 13. Full demonstration to implement and test

Use the backend guide's seeded scenario. Seeded data: `R1` pins `DB_LAB` to Monday morning; `R2` limits it to Prof. Rao; `v1` is published/anchored. Add `R3` from a Hindi voice rule (or typed fallback) making Prof. Rao unavailable Monday morning.

1. Sign in using a **real newly implemented demo auth account**, not merely a local React flag.
2. Dashboard loads **actual** seeded schedule/health.
3. Intake text/voice extracts R3 as draft; animated rule card appears.
4. Review R3; confirm it; registration succeeds on Anvil.
5. Solve; display indeterminate progress; backend identifies infeasibility and core `{R1,R2,R3}`.
6. Explain conflict; show **solver-verified** alternatives.
7. Select a protected option; display demo Anvil owner account; demonstrate unauthorized approval rejection and proper owner approval.
8. Apply approved option; solve again; inspect minimal-change result and moved sessions.
9. Publish `v2`; verify checker and chain anchor, then offer JSON/CSV/ICS.
10. Verify original JSON passes, and a modified copy fails.
11. Inspect actual chain events and measured scoreboard (recorded label in mock mode).
12. Sign out; `/app/*` becomes inaccessible without an active session.

Ensure fixture IDs match the seeded rule IDs, as required by the backend guide. All claims must match backend observations.

---

## 14. Testing and acceptance gates

### Visual quality

- Matches shadcn dashboard style: no heavy shadows/gradients on cards, neutral typography, consistent 12px radii and spacing.
- Auth pages are clean and aesthetically restrained in desktop, tablet, mobile, light and dark mode.
- Routes switch smoothly **without sidebar flicker** or duplicated page content.
- Four metric cards use a small stagger; tab active state glides; drawers, dropdowns and status changes animate lightly.
- Ambient background is barely visible, noninteractive and fully disabled under reduced-motion preference.
- Loading skeletons do not create large layout shifts.

### Functional

- Sign-up, sign-in, `/auth/me`, sign-out and session expiry really work and are enforced by the server.
- Form errors, retry states, submission spinners and navigation function correctly.
- Each user action calls the expected actual backend function through the HTTP adapter.
- Frontend data matches backend output (no fabricated chart values, conflict resolutions, chain receipts or percentages).
- Published schedule can be reloaded after navigation; JSON/CSV/ICS bytes round-trip correctly.
- Non-owner approval is rejected by the chain; applying unapproved options fails.
- Tampered schedule verification fails; confirmed-only rules are enforced.

### Backend regression

Run `pytest -q` and the guide's tests for feasible schedule, exact conflict core, verified options, minimal-change scheduling, checker violations, stable hash, parameter validation, chain integration and sheet cache. Run `forge test`. Use healthcheck for Gemma/Docker/Anvil and the audio test where relevant. Fix regressions; never suppress failures to pass a demo.

### Security

- Auth cookies are HttpOnly, Secure in HTTPS, configured SameSite; CSRF and rate limits are tested.
- Backend checks permissions for every protected endpoint, not just route guard.
- No tokens/private keys/wallet secrets in browser storage or bundle.
- No direct cross-organization reads when multi-tenancy is eventually introduced.
- File upload permissions/size and safe input validation tested.

### Performance

- On a normal laptop, route switches and tab selections feel immediate; no jank in KPI cards or schedule changes.
- Ambient animation does not materially increase idle CPU usage; remove it if it does.
- Test 320px mobile width, 768px tablet and wide desktop, plus reduced-motion and keyboard-only navigation.

---

## 15. Growth path for universal organizations and events

The generalized product scope from the broader GeCompose discussion is **a roadmap, not a claim about the uploaded v1 backend**.

### Phase 1 — ship the current college demo with a universal-looking shell

Preserve fixed slot grid and four rule types. Add auth, clean React UI, FastAPI adapter, genuine state management and complete end-to-end demo. For workspace picker, show a single clearly labeled “College demo” workspace unless persistence is genuinely implemented.

### Phase 2 — general scheduling model and domain templates

Implement tenant-scoped `Organization`, `Workspace`, `Event`, `Session`, `Participant`, `Venue`, `Resource`, `TimeInterval`, `Constraint`, `RuleOwner`, `Approval` and `ScheduleVersion`. Introduce arbitrary time zones, real time intervals/durations, capacity, no-overlap, precedence/setup/teardown, soft preferences and configurable optimization. Support templates for colleges, seminars/conferences, festivals and government meetings as actual constraint schemas.

### Phase 3 — global coordination

Add SSO/OIDC, organization-wide RBAC, explicit inter-org free/busy sharing, external calendar integrations, notification delivery, regional governance choices, real approval identity binding, load-safe job processing and production audit strategy. Do not use the demo chain as a substitute for regulated sector access controls.

### Domain-oriented UI labels

| Academic v1 | Universal product label |
|---|---|
| Teacher | Participant / assigned person |
|---|---|
| Room | Venue / resource |
|---|---|
| Class | Session / event |
|---|---|
| Timetable | Schedule |
|---|---|
| Review rules | Constraints |
|---|---|
| Faculty approval | Rule-owner approval |

**Compatibility:** keep backend schema names as-is in Phase 1; translate labels at the UI layer. Don't prematurely rename Python model fields and break the supplied tests.

---

## 16. Coding agent build order

**Read first:** this guide, `BACKEND_GUIDE(1).md`, actual repo `README`, `frontend/` contents, any available `FRONTEND_SETUP.md` and `WORKFLOW_AND_USAGE.md`. Those two are merely referenced in the supplied backend guide; if absent, note absence and proceed using present files, not fabricated content.

**Build sequentially, keeping the app executable after each step:**

1. Inventory repo; run supplied backend tests and healthcheck in mock mode. Identify real module names and importable functions.
2. Scaffold Vite/React/TypeScript/shadcn (if not already present); establish theme tokens, layout shell, Lucide icons, routing.
3. Add static component scaffolds matching the design reference; no fake success data or placeholder "live" metrics.
4. Implement central motion tokens, route transitions, cards, drawer and tab motion. Implement reduced-motion behavior.
5. Add CSS ambient background and inspect performance; leave Three.js out.
6. Implement FastAPI adapter with health/roster/rules/solve first, validated schemas, unified errors, protected routes.
7. Implement real auth persistence, password hashing, session cookies, CSRF/permissions, public auth pages, guards and sign-out.
8. Wire intake and rule review, including binary uploads and on-chain confirmation results.
9. Wire solve/conflict/explanation/options/approvals/re-solve with truth-based progress states.
10. Wire schedule/why/publish/verify/downloads; add persistence/read endpoints as needed.
11. Wire scoreboard, chain log, health diagnostics and fixture labeling.
12. Add comprehensive tests, responsive/dark/a11y review, documentation, example environment files and end-to-end demo.

### Required AI work product on completion

- A brief architecture summary and list of files changed.
- Start commands for frontend, FastAPI, Python services and Anvil in mock and real-model modes.
- Environment variable inventory (`.env.example`; no secrets committed).
- Endpoint list/OpenAPI access path and which functions are **existing** versus **new**.
- Test commands with actual pass/fail output, and an honest list of anything not implemented.
- Screenshot/recording evidence of sign-in, dashboard, rule review, feasible/conflict flow and verification when automation is available.
- A short, reproducible demonstration script.

---

## 17. Agent-ready final instruction

> **Implement GeCompose as a production-quality-looking, fully functional React/shadcn/ui application with a minimalist dashboard, polished auth screens, seamless navigation, restrained card animations, clear real operation progress and a barely visible CSS ambient background. Use the existing Python backend as the authoritative source for scheduling, AI extraction, validation, conflict verification, Anvil approvals and publishing. Add a thin authenticated FastAPI web adapter and real session-based authentication; do not pretend these exist already. Make all status labels, values, progress and permissions truthful. Preserve the backend's narrow v1 college demo while keeping the component architecture adaptable to the longer-term universal scheduling vision. Prioritize correctness, accessibility and performance above decorative motion. Do not claim a feature is complete until exercised end-to-end and tested.**

---

## 18. Official references

- shadcn/ui dashboard visual reference: https://ui.shadcn.com/examples/dashboard
- shadcn/ui Vite setup: https://ui.shadcn.com/docs/installation/vite
- shadcn/ui Sidebar: https://ui.shadcn.com/docs/components/sidebar
- Motion for React layout transitions: https://motion.dev/docs/react-layout-animations
- Motion for React exit transitions: https://motion.dev/docs/react-animate-presence
- FastAPI security guidance: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- OWASP session guidance: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html

**Source fidelity note:** The source backend document explicitly labels its sample code **untested** and refers to `FRONTEND_SETUP.md` and `WORKFLOW_AND_USAGE.md`; those files were not supplied in this conversation. The integration and auth design above are new implementation proposals, not existing backend features.
