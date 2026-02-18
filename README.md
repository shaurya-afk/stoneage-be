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
- **Tesseract OCR** + **poppler** for scanned PDFs (layout extraction from image-based pages)
- **Supabase** (auth + optional DB), **PyJWT** for token verification
- Python 3.11+

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Local setup (Windows) – scanned PDFs

For **scanned** PDFs (image-based, no selectable text), the app uses two **system tools** that are not Python packages. You need to install them once on your machine.

| Tool | What it does | Why we need it |
|------|----------------|----------------|
| **Poppler** | Converts PDF pages into images (via `pdftoppm`) | The library `pdf2image` uses Poppler to turn each PDF page into an image so we can run OCR on it. |
| **Tesseract** | OCR engine: reads text from images | After Poppler gives us images of each page, Tesseract extracts the text (and positions) from those images. |

**1. Install Tesseract (Windows)**

- Open: **https://github.com/UB-Mannheim/tesseract/wiki** (official Windows builds).
- Download the latest **Windows installer** (e.g. `tesseract-ocr-w64-setup-5.x.x.exe`).
- Run the installer. Use the default install path (e.g. `C:\Program Files\Tesseract-OCR`).
- **Add to PATH:**  
  - Windows key → search “Environment variables” → “Edit the system environment variables” → **Environment Variables**.  
  - Under “System variables”, select **Path** → **Edit** → **New** → add:  
    `C:\Program Files\Tesseract-OCR`  
  - Confirm with OK. **Restart your terminal** (and IDE if it uses its own terminal).

**2. Install Poppler (Windows)**

- Open: **https://github.com/oschwartz10612/poppler-windows/releases**.
- Download the latest **zip** (e.g. `Release-24.08.0-0.zip`).
- Extract it to a folder, e.g. `C:\Program Files\poppler` or `C:\Users\<You>\poppler`.  
  - Inside you’ll see a folder like `poppler-24.08.0\Library\bin` that contains `pdftoppm.exe`.
- **Either** add that `bin` folder to your system **Path** (same steps as for Tesseract),  
  **or** set it in your backend `.env` so the app finds Poppler without touching PATH:
  ```env
  POPPLER_PATH=C:/Program Files/poppler/poppler-24.08.0/Library/bin
  ```
  (Replace with the path that actually contains `pdftoppm.exe` on your PC. Use **forward slashes** in `.env` so backslashes aren’t misinterpreted.)

**3. Check**

- Restart the terminal, go to `be`, activate the venv, run `uvicorn app.main:app --reload`.
- Upload a scanned PDF again; the “poppler” and “tesseract” errors should be gone.

Copy `.env.example` to `.env` and set:

| Purpose | Env vars |
|--------|----------|
| **Supabase** | `SUPABASE_URL`, `SUPABASE_ANON_KEY` (or service key); `SUPABASE_JWT_SECRET` for token verification |
| **Email** | **Resend** (recommended on Render): `RESEND_API_KEY`, `MAIL_FROM` (optional; defaults to `onboarding@resend.dev`). **Or SMTP:** `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `MAIL_FROM` |
| **DB (optional)** | `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` — or a single `DATABASE_URL` |
| **Scanned PDF (Windows)** | `POPPLER_PATH` – path to Poppler `bin` (folder containing `pdftoppm.exe`) if not on PATH |

**DB on Render (Supabase):** The direct Postgres port (5432) often fails from Render with "Network is unreachable". Use Supabase’s **connection pooler** instead: in [Supabase](https://supabase.com/dashboard) → your project → **Settings** → **Database** → **Connection string** → choose **URI** and the **"Transaction"** (or "Session") pooler. That URL uses host `aws-0-<region>.pooler.supabase.com` and **port 6543**. Set that as `DATABASE_URL` on Render (or split into `DB_HOST`, `DB_PORT=6543`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`). The app will add `?sslmode=require` if missing.

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

### Scanned PDFs (OCR) – use Docker

Extraction supports **scanned** PDFs (image-based, no selectable text) via **Tesseract OCR**. Tesseract is a system binary, not a Python package, so it is **not** installed by the default Render Python buildpack.

To fix the error *"tesseract is not installed or it's not in your PATH"*:

1. Deploy the backend with **Docker** on Render (not native Python).
2. In the Render dashboard: create or edit your service → set **Environment** to **Docker**.
3. Set **Root Directory** to `be` (so the build context is `be` and the Dockerfile at `be/Dockerfile` is used). Leave **Dockerfile Path** empty so it defaults to `./Dockerfile` inside that root.
4. The repo’s `be/Dockerfile` installs Tesseract and poppler; redeploy so the new image is used.

After redeploying with Docker, scanned PDFs (e.g. "Diamond - Extrusion Machine.pdf") will work.
