# IdeaForge

Hackathon product (package name `ideaforge`) that turns a business idea into a deployed SaaS via an agent pipeline: research, strategy brief, build, Vercel deploy, Stripe checkout, audit trail.

Local folder is `Superai`. Remote is `mchawda/ideaforge`.

**Operator app:** [https://idea-forge-eta-six.vercel.app](https://idea-forge-eta-six.vercel.app)

**GitHub:** [github.com/mchawda/ideaforge](https://github.com/mchawda/ideaforge)

Standalone marketing HTML lives at `ideaforge-website.html` (not a separate live domain in this repo).

## Stack

- `apps/web`: Next.js 16, React 19, Tailwind v4
- `orchestrator/`: FastAPI (Python)
- SQLite session store, Vercel / v0, Exa, Stripe
- Bun workspaces at repo root

## Run locally

```bash
cp .env.example .env
# fill API keys

bun install
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

bun run start
# or: bun run dev:api  and  bun run dev:web
```

Web: [http://localhost:3000](http://localhost:3000). API: [http://localhost:8000](http://localhost:8000).

Architecture notes: `ARCHITECTURE.md`.
