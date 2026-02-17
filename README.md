# Stone Age

## PDF to Excel Data Extraction API

Backend API that extracts structured data from PDFs (e.g. invoices, resumes), returns it as JSON, and generates an Excel report. Supports auth via Supabase and optional email delivery of the report to the signed-in user.

## Features

- **PDF extraction** – Parse layout, tables, and text; extract fields (invoice number, date, amounts, skills, etc.) with optional LLM support
- **Excel export** – Generate `.xlsx` from extraction results
- **Auth** – Supabase: email/password signup & signin, Google OAuth; JWT verification (ES256 JWKS + legacy HS256)
- **Email** – Optional SMTP: send the Excel file to the authenticated user’s email after extraction

## Tech

- **FastAPI**, **pdfplumber** / **pypdf**, **spaCy** (en_core_web_sm), **pandas** / **openpyxl**
- **Supabase** (auth + optional DB), **PyJWT** for token verification
- Python 3.11+

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Copy `.env.example` to `.env` and set:

| Purpose | Env vars |
|--------|----------|
| **Supabase** | `SUPABASE_URL`, `SUPABASE_ANON_KEY` (or service key); `SUPABASE_JWT_SECRET` for token verification |
| **Email** | **Resend** (recommended on Render): `RESEND_API_KEY`, `MAIL_FROM` (optional; defaults to `onboarding@resend.dev`). **Or SMTP:** `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `MAIL_FROM` |
| **DB (optional)** | `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` |

Run:

```bash
uvicorn app.main:app --reload
```

API: `http://localhost:8000` · Docs: `http://localhost:8000/docs`

## API overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/signup` | Email/password signup |
| POST | `/api/v1/auth/signin` | Email/password signin |
| GET | `/api/v1/auth/google/url` | Get Google OAuth URL |
| POST | `/api/v1/auth/google` | Sign in with Google ID token |
| POST | `/api/v1/extract` | Upload PDF, extract data; returns JSON + `excel_path`; emails Excel if SMTP set and user authenticated |
| GET | `/api/v1/extract/{raw_id}/download` | Download stored PDF (auth required) |
| GET | `/health` | Health check |

**Extract** expects `Authorization: Bearer <access_token>` when auth is configured, plus form/body: `file` (PDF), `document_type`, `fields` (comma-separated).

## Deploy (Render)

- Use **Python 3.11** (e.g. `.python-version` with `3.11`). Python 3.14 is not compatible with spaCy/Pydantic v1.
- Set all required env vars in the Render dashboard.
- **Email:** SMTP is often blocked on Render. Use **Resend**: sign up at [resend.com](https://resend.com), create an API key, then set `RESEND_API_KEY` (and optionally `MAIL_FROM=onboarding@resend.dev`) on Render.
