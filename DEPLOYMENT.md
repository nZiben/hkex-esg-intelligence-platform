# Deployment Guide

## 1) Supabase (Postgres + pgvector)

1. Create a Supabase project.
2. Run SQL in `infra/supabase.sql`.
3. Copy connection string into `DATABASE_URL`.

## 2) API on Render

1. Create a new Web Service from this repo.
2. Root directory: `apps/api`.
3. Use `infra/render.yaml` or manual Docker deployment.
4. Set env vars:
   - `DATABASE_URL`
   - `OPENAI_API_KEY`
   - `OPENAI_BASE_URL=https://rtekkxiz.bja.sealos.run/v1`
   - `LLM_MODEL`
   - `EMBEDDING_MODEL`

## 3) Web on Vercel

1. Import repo on Vercel.
2. Set project root to `apps/web`.
3. Set env var `NEXT_PUBLIC_API_BASE_URL=<render-api-url>`.
4. Deploy.

## 4) Ingest Job

Run once after deployment environment variables are set:

```bash
python scripts/bootstrap_ingest.py --data-dir data
```

For quick smoke seed:

```bash
python scripts/bootstrap_ingest.py --data-dir data --max-pdfs 30 --skip-embeddings
```
