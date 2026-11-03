# Mobile refactor — documentation index

> Board: **Mobile Refactor** · Columns: Backlog · Discovery · Design · In Progress · Review & Demo · Done
> Scope: the customer-facing web client (`/home/codx-junior-projects/codx-junior/client`).

---

## 1. Reading order

| # | Document | What it is | Status |
|---|---|---|---|
| 1 | [`mobile-current-status.md`](./mobile-current-status.md) | Full audit of the mobile state: 35-app inventory, navigation model, shell audit, per-screen consistency, 10 defects (D1–D10), duplication map, constraints | v1 — **superseded in parts** |
| 2 | [`status-verification-delta.md`](./status-verification-delta.md) | Re-verification against the files on disk: 11 corrections to v1, current shell/router facts | v2 — **authoritative** |
| 3 | [`mockups-brief.md`](./mockups-brief.md) | Brief handed to the Mockups / Designer profile: constraints, 8 required frames, comparison criteria | ready |
| 4 | [`approaches/01-shell-first.md`](./approaches/01-shell-first.md) | **Approach A** — wrap the screens in one shell; cheapest, lowest risk | proposed |
| 5 | [`approaches/02-adaptive-pages.md`](./approaches/02-adaptive-pages.md) | **Approach B** — one component per screen with two densities; removes the duplication | proposed |
| 6 | [`approaches/03-launcher-stack.md`](./approaches/03-launcher-stack.md) | **Approach C** — launcher + per-module stack + mobile registry; phone as its own surface | proposed |

## 2. The three approaches at a glance

| | A · Shell-first | B · Adaptive pages | C · Launcher + stack |
|---|---|---|---|
| Nav surface | bottom bar (5) + More sheet | bottom bar + More sheet + per-screen patterns | launcher (L0) + constant bottom bar (4) + More sheet |
| Back | `router.back()` / `meta.parent` | `meta.parent` + container-query layouts | explicit stack (L2→L1→Launcher) |
| Screens rewritten | 0 | ~15 migrated, 4 re-laid out | 3–4 new mobile-specific screens + launcher/sheet |
| Fixes | D1, D2, D3, D4, D6, D7, D9 | **all of D1–D10 + §7 duplication** | D1–D4, D6–D10 (D5 partial) |
| Leaves broken | D5, D8, D10, all duplication | — | `PENDING` map for non-migrated modules |
| Effort | ~1 sprint | 2–3 sprints | 3–4 sprints |
| Risk | low | medium-high | high |
| Reversible | yes (one wrapper) | per screen (flag) | yes (registry + one route) |
| Design cost | 1 shell + 5 bar items | shell + 2 densities × ~15 screens | launcher + stack + sheet + 4 mobile screens |

**Shared foundation (identical in all three):** `useViewport()` as the single breakpoint
source, one shell that owns scroll + safe areas, a `/desktop` device guard, a mounted
navigation surface, and the D6 chat fix. Whichever approach is chosen, the first increment is
the same.

## 3. Recommendation (for the decision record — not a decision)

Ship **A first, behind `ui.mobileShell`**, because the product currently has *no* usable
phone navigation and A is the only approach that can close D2/D3/D6 without touching a screen.
Then treat **B as the migration path** per screen (it is A's shell plus a per-screen contract,
so no work is thrown away) and adopt **C's `MOBILE_APPS.fits` registry idea** even if the
launcher itself is not built — a per-app "does this fit on a phone?" flag is what prevents the
current failure mode from coming back.

C is the right answer only if mobile is decided to be a first-class surface.

## 4. Decision record (fill when the approaches are reviewed)

```md
Decision:        A | B | C | A+B hybrid | other
Decided by:
Date:
Rationale:
Rejected because:
First increment (M1) scope:
Flag name:
Demo device(s) / viewports:
```

## 5. Open questions blocking the decision

1. Is mobile a **support surface** (triage chat + tasks) or a **first-class surface**?
2. `ChatEntryMobile.vue`: create the thin component (A/C) or delete the fork and make
   `ChatEntry` responsive (B)?
3. Do chat / workspaces / browsers keep two components, or is collapsing them in scope?
4. Who owns the 35-app "fits on a phone" classification — product or engineering?
5. Is a smoke-test setup in scope? (`tests/` currently holds only `fileChangeParser.test.mjs`;
   every acceptance criterion in these documents is currently verified by hand.)

## 6. Task map for the board

| Id | Task | Column | Depends on | Document |
|---|---|---|---|---|
| M0 | Mobile audit (current status) | Done | — | `mobile-current-status.md` + `status-verification-delta.md` |
| M1 | Shell + primitives + D6 fix (shared foundation) | Backlog | M5 | approaches A/B/C §4 |
| M2 | Approach A prototype behind flag | Backlog | M1 | `approaches/01-shell-first.md` |
| M3 | Approach B per-screen migration | Backlog | M5 | `approaches/02-adaptive-pages.md` |
| M4 | Approach C launcher + stack | Backlog | M5 | `approaches/03-launcher-stack.md` |
| M5 | **Decide the mobile strategy (A/B/C)** | Design | mockups | this document, §4 |

> Note: the tasks above were requested on the **Mobile Refactor** board; if the board shows
> no cards, the task store did not persist them — re-create from this table and verify with
> the board's list action before dispatching work.
