# Deploying Smart Inventory

## Current production setup

| Item | Value |
|---|---|
| Host | Railway (project `helpful-wisdom`, service `smart-inventory`) |
| Live URL | https://smart-inventory-production-a1f3.up.railway.app |
| Database | Railway MySQL (`mysql.railway.internal`), private network only |
| Container | `Dockerfile` → `gunicorn --workers 2 app:application`, port from `$PORT` |
| Health check | `GET /health` → 200 |

Only one public domain exists. The old duplicate
`smart-inventory-production-64ff.up.railway.app` was deleted — it now returns 404.

## How deploys work (decision: CLI, not GitHub auto-deploy)

Railway's GitHub auto-deploy is broken for this repo: the dashboard's branch
picker returns "Auto deploy unavailable — Could not load branches" even with the
Railway GitHub App installed. It needs a Railway↔GitHub OAuth re-login to fix.
**We are not chasing that.** Deploys go through the CLI from the repo root:

```bash
git push origin master          # keep GitHub as the source of record
railway up --ci                 # build + deploy the working tree
railway status                  # confirm the new deployment ID is Online
curl -s https://smart-inventory-production-a1f3.up.railway.app/health
```

`railway up` uploads the working tree, so commit first — otherwise prod drifts
from GitHub. `--ci` streams build logs and exits non-zero on failure, which makes
it usable from a script or CI later.

### Rollback

```bash
railway redeploy --yes    # redeploy a previous deployment from the dashboard,
                          # or: git checkout <good-sha> && railway up --ci
```

### Backups

Railway SSH is unavailable from this machine and `mysqldump` is not installed,
so the backup path that actually runs is a JSON snapshot over the same
`DATABASE_URL` the app uses:

```bash
python scripts/backup_db.py                                    # backups/inventory-<utc>.json
python scripts/backup_db.py --restore backups/inventory-<utc>.json --yes
```

Restore is destructive (empties every table first) and refuses to run without
`--yes`. `backups/` is git- and docker-ignored. Verified by
`tests/backend/test_backup.py` (dump → wipe → restore round trip).

The app also refuses to boot if neither `DATABASE_URL` nor `MYSQL_URL` is set —
without them it used to fall back to a container-local SQLite file whose writes
vanished on the next deploy.

### Environment variables (set on the Railway service)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | MySQL connection string (provided by the MySQL service, private URL) |
| `SECRET_KEY` | Flask session signing key |
| `SESSION_COOKIE_SECURE` | `true` in production (HTTPS only) |
| `PREDICTION_INTERVAL_DAYS` | How often predictions are regenerated |
| `LOW_STOCK_THRESHOLD` | Default low-stock cutoff |

`railway variables` lists names and values. Never commit them.

## Free hosting: what actually fits this app

The app is a long-running Flask process holding a MySQL connection pool.
Anything serverless that kills idle processes or expects a serverless-native
database is a poor fit.

| Platform | Free option in 2026 | Fits this app? |
|---|---|---|
| **Railway** (current) | Trial credit, then Free plan ≈ $1/mo credit (no rollover); Hobby $5/mo | Yes — best fit. Only realistic long-term option is the $5 Hobby plan. Trial ends ~5 days out. |
| **Render** | Free web service: 512 MB / 0.1 CPU, spins down after 15 min idle, ~1 min cold start, 750 instance-hrs/mo | Yes for the app; **free Postgres expires 30 days after creation** (then deleted after a 14-day grace). Has a real free tier for a demo, unsuitable for keeping data. |
| **Koyeb** | Free instance exists (512 MB / 0.1 vCPU, sleeps after 1 h) but new accounts are pushed to Pro $29/mo with a $29 card hold | No — the free door effectively closed in Feb 2026. |
| **Fly.io** | No free tier since Oct 2024; trial is 2 h runtime / 7 days. Shared-cpu 1x ≈ $2–3/mo + volume | Yes, cheap and closest to a VPS, but you manage volumes, Postgres/MySQL, and deploys via `flyctl`. |
| **Cloud Run / App Engine** | Generous free tier, but scales to zero, request timeouts, and MySQL must be Cloud SQL (~$10/mo) or external | No — the free tier's value disappears once you need a database. |
| **VPS** (Hetzner CX22 ≈ €4/mo) | None free | Yes — cheapest always-on, but you own OS patching, TLS, backups, MySQL. |
| **Vercel / Netlify** | Free | **No.** Serverless functions: 4.5 MB payload cap, no persistent DB connection pool, no long-lived MySQL. A Flask app technically runs, but you would still need separate hosted MySQL (PlanetScale/Aiven/TiDB), all of which are trial-limited. More moving parts, not less. |

**Decision:** stay on Railway. If the trial lapses, the fallback order is
Render (accepting the 30-day DB reset) → Fly.io shared CPU → Hetzner VPS.

> `render.yaml` at the repo root is stale — it references a Render Postgres
> database and `plan: free`. Do not use it as-is; Render's free database is
> deleted 30 days after creation.
