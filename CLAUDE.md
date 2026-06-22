# ExamTarget — Claude Code Instructions

Math worksheet generator for classroom teachers and homeschool parents. Verified answer keys, AI step-by-step solutions, multi-version generation, clean print + Word export.

---

## Architecture

Two services, strict separation of concerns:

| Service | Path | Stack | Responsibility |
|---|---|---|---|
| **web** | `apps/web/` | Next.js 15, TypeScript, Tailwind CSS, Clerk, Stripe | UI, routing, auth state. **Zero math logic.** |
| **engine** | `apps/engine/` | Python FastAPI, SymPy, Supabase, Gemini | All math generation, verification, export, billing enforcement. |

The web app calls the engine over HTTP. The engine owns every computation. Never put math logic in `apps/web/`.

---

## The One Rule That Cannot Be Broken

**SymPy computes every answer. SymPy is the source of truth.**

- Gemini's only job is to write human-readable step-by-step explanations toward a known answer.
- Every AI output must be verified against SymPy's exact answer before it is stored or returned.
- If the AI's final answer does not match SymPy's: reject, regenerate. Never serve unverified output.

---

## Problem Generation Rules

1. **Seeded and deterministic.** The same `(topic, seed, params)` must always produce the same problem. A worksheet is reproducible and cacheable by its seed.

2. **Reject degenerate problems at generation time** — do not let them reach the user:
   - Zero or undefined denominators
   - Expressions that do not simplify to a finite real value
   - Answers uglier than the difficulty allows (e.g. `137/29` on easy difficulty — use a cleanliness threshold)
   - Regenerate with the next seed until a valid problem is produced.

3. **`sympy.latex()` for all math rendering.** Never hand-format math strings. Every problem, answer, and step must go through SymPy → LaTeX → KaTeX.

4. **Tag every topic with standard codes.** CCSS is the minimum (e.g. `A-REI.3`, `A-SSE.3`). Add TEKS / FL B.E.S.T. later as a metadata field, not a code change.

---

## Caching Rule

```
cache_key = hash(topic + seed + params)
```

Before calling Gemini, check Supabase for a verified solution at that key. If it exists, return it. **Never call Gemini for a problem we have already solved.**

Store only after SymPy verification passes.

---

## Free-Tier Infra Constraints

| Service | Tier | Constraint |
|---|---|---|
| Vercel | Hobby | Serverless functions; minimise bundle size and cold-start time |
| Clerk | Free | Limited MAUs; do not add unnecessary auth calls |
| Supabase | Free | 500 MB DB, 2 GB bandwidth; use the cache aggressively |
| Gemini | Free quota | Rate-limited; the cache above is mandatory, not optional |

Design every feature with these limits in mind. If a design requires paid infra to function correctly, flag it before building.

---

## Print Quality

**Print quality is a product feature, not polish.**

PDFs must look at least as clean as Kuta Software output: proper work spacing, fit-to-page, readable equations, name/date/period header. Do not mark a PDF task complete until the output passes a visual comparison against Kuta on paper.

---

## Coding Conventions

### TypeScript (`apps/web/`)
- `strict: true` in `tsconfig.json`. No `any`, ever.
- All API response shapes typed with explicit interfaces — no `unknown` casts without a guard.
- Env vars via `process.env.NEXT_PUBLIC_*` (client) or `process.env.*` (server); never hardcoded.

### Python (`apps/engine/`)
- Type hints on every function signature.
- All route handlers return a typed Pydantic model — no bare `dict` returns.
- No secrets in source code; always load from environment variables via `python-dotenv`.
- Use `sympy.Rational` / `sympy.Integer` for exact arithmetic; never `float` for answer comparison.

---

## Env Vars Reference

| Var | Used by |
|---|---|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | web |
| `CLERK_SECRET_KEY` | web, engine |
| `NEXT_PUBLIC_ENGINE_URL` | web |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | web |
| `STRIPE_SECRET_KEY` | web |
| `STRIPE_WEBHOOK_SECRET` | web |
| `SUPABASE_URL` | engine |
| `SUPABASE_SERVICE_KEY` | engine |
| `GEMINI_API_KEY` | engine |

Copy `.env.example` to `.env.local` (web) and `apps/engine/.env` (engine) before running locally.

---

## Run Locally

```bash
# Web (Next.js)
pnpm dev                          # → http://localhost:3000

# Engine (FastAPI)
cd apps/engine
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000   # → http://localhost:8000/health
```
