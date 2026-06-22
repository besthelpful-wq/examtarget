# ExamTarget

A math worksheet generator for classroom teachers and homeschool parents. Verified answer keys (SymPy), AI step-by-step solutions, multi-version generation, clean print + Word export.

## Stack

| Layer | Tech |
|---|---|
| Web | Next.js 15, TypeScript, Tailwind CSS, App Router |
| Engine | Python FastAPI, SymPy |
| Auth | Clerk |
| Payments | Stripe |
| AI | Gemini 2.0 Flash |
| Math render | KaTeX |

## Getting started

### Prerequisites

- Node.js 20+
- pnpm 9+
- Python 3.11+

### 1. Clone and install

```bash
git clone <repo>
cd examtarget
pnpm install
```

### 2. Set up environment variables

```bash
cp .env.example .env.local   # fill in the values
```

Copy the ENGINE block into `apps/engine/.env` as well.

### 3. Run apps/web (Next.js)

```bash
pnpm --filter web dev
# → http://localhost:3000
```

### 4. Run apps/engine (FastAPI)

```bash
cd apps/engine
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# → http://localhost:8000
# → http://localhost:8000/health  {"status":"ok"}
```

### 5. Run both together (from repo root)

Open two terminals and run the commands in steps 3 and 4 simultaneously.

## Project layout

```
examtarget/
├── apps/
│   ├── web/       # Next.js 15 frontend
│   └── engine/    # FastAPI + SymPy backend
├── .env.example
├── pnpm-workspace.yaml
└── CLAUDE.md
```

## Architecture principle

**SymPy is the source of truth for every answer.** Gemini only writes human-readable step explanations; every AI output is verified against SymPy before it is served to the user.
