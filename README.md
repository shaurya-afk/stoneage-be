# Stone Age

**AI-powered PDF data extraction backend.** Extract structured data from invoices, receipts, reports, and custom document formats. Supports both text-based and scanned PDFs via OCR, with LLM-backed extraction and export to JSON and Excel.

---

## Features

- **Structured extraction** — Extract configurable fields (invoice number, date, amounts, line items, etc.) from PDFs using layout analysis, tables, and optional LLM (Gemini).
- **Scanned PDF support** — OCR pipeline with Tesseract and Poppler: image-based PDFs are converted page-by-page and processed like native text.
- **LLM-powered parsing** — Google Gemini for semantic extraction with JSON output; regex and spaCy hints improve accuracy.
- **Structured output** — Response aligned to requested fields; export as JSON and Excel (.xlsx).
- **Auth** — Supabase: email/password signup & signin, Google OAuth; JWT verification (ES256 JWKS + legacy HS256).
- **Email** — Optional: send the generated Excel to the authenticated user (Resend API or SMTP).
- **Production-ready** — Docker image with Tesseract and Poppler; Render-friendly; configurable timeouts for long-running extractions.

---

## Architecture

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                      Stone Age API (FastAPI)                  │
                    └─────────────────────────────────────────────────────────────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    ▼                           ▼                           ▼
            ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
            │   Auth        │           │   Extract     │           │   Health      │
            │   (Supabase)  │           │   (PDF → JSON │           │   /health     │
            │   signup/signin│           │    + Excel)   │           │               │
            └───────────────┘           └───────┬───────┘           └───────────────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    ▼                           ▼                           ▼
            ┌───────────────┐           ┌───────────────┐           ┌───────────────┐
            │ PDFProcessor  │           │ Document      │           │ ExcelGenerator│
            │ • is_scanned? │─────────►│ Formatter     │─────────►  │ (pandas +     │
            │ • text/tables │           │ (spaCy +      │     │      │  openpyxl)    │
            │ • OCR path    │           │  regex hints) │     │      └───────────────┘
            └───────────────┘           └───────┬───────┘     │
                    │                           │             │
                    │ (if scanned)              ▼             │
                    │                   ┌───────────────┐    │
                    └──────────────────►│ LLMProcessor  │────┘
                         Tesseract      │ (Gemini)      │
                         + Poppler      │ JSON output   │
                                        └───────────────┘
```

**Flow:** Upload PDF → detect text vs scanned → extract layout/tables (or OCR) → format text + build hints → LLM extraction → validate/parse JSON → generate Excel → return JSON + `excel_path`.

---

## Tech stack

| Layer        | Technology |
|-------------|------------|
| API         | FastAPI, Uvicorn |
| PDF text    | pdfplumber, pypdf |
| PDF → images| pdf2image, **Poppler** (pdftoppm) |
| OCR         | **Tesseract** (pytesseract) |
| NLP / hints | spaCy (en_core_web_sm), regex |
| LLM         | Google Gemini (google-genai) |
| Export      | pandas, openpyxl (.xlsx) |
| Auth        | Supabase (JWT, OAuth) |
| Email       | Resend or SMTP |
| DB (optional)| PostgreSQL (SQLAlchemy, psycopg2) |
| Runtime     | Python 3.11+ |

---

## Installation

### Docker (recommended for production and OCR)

Requires no local Tesseract/Poppler install.

```bash
git clone <repo-url>
cd be
docker build -t stone-age .
docker run -p 8000:8000 --env-file .env stone-age
```

API: `http://localhost:8000` · Docs: `http://localhost:8000/docs`

### Local development

1. **Python 3.11+** and venv:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

2. **Optional – scanned PDFs:** Install system dependencies.

| Tool      | Role |
|----------|------|
| **Poppler** | PDF → images (`pdftoppm`); used by `pdf2image`. |
| **Tesseract** | OCR on page images. |

- **Windows:** Install [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) and [Poppler](https://github.com/oschwartz10612/poppler-windows/releases); add their `bin` folders to `PATH`, or set `POPPLER_PATH` in `.env` to the Poppler `bin` directory.
- **Linux (Debian/Ubuntu):** `sudo apt-get install tesseract-ocr tesseract-ocr-eng poppler-utils`

3. **Run:**

```bash
uvicorn app.main:app --reload
```

---

## Environment variables

Copy `.env.example` to `.env` and configure as needed.

| Purpose        | Variables |
|----------------|-----------|
| **LLM (required for extraction)** | `API_KEY` — Google AI / Gemini API key |
| **Auth**       | `SUPABASE_URL`, `SUPABASE_ANON_KEY` (or `SUPABASE_SERVICE_KEY`); `SUPABASE_JWT_SECRET` for JWT verification |
| **Email**      | **Resend:** `RESEND_API_KEY`, `MAIL_FROM` (optional). **Or SMTP:** `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `MAIL_FROM` |
| **Database (optional)** | `DATABASE_URL` or `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` |
| **OCR (local)** | `POPPLER_PATH` — path to Poppler `bin` if not on `PATH` |

---

## API usage

### Extract (main endpoint)

**Request**

```http
POST /api/v1/extract
Content-Type: multipart/form-data
Authorization: Bearer <access_token>   # optional; required for email + stored PDF download

file: <PDF file>
document_type: invoice
fields: invoice_number,invoice_date,total_amount,vendor_name
```

**Response (200)**

```json
{
  "invoice_number": "INV-2024-001",
  "invoice_date": "2024-01-15",
  "total_amount": "1,250.00",
  "vendor_name": "Acme Corp",
  "excel_path": "generated_excel/extraction_a1b2c3d4.xlsx",
  "email_note": "queued"
}
```

For multi-row extractions the API may return `"extracted": [ {...}, ... ]` with the same `excel_path`.

**Other endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/v1/auth/signup` | Email/password signup |
| POST   | `/api/v1/auth/signin` | Email/password signin |
| GET    | `/api/v1/auth/google/url` | Google OAuth URL |
| POST   | `/api/v1/auth/google` | Sign in with Google ID token |
| GET    | `/api/v1/extract/{raw_id}/download` | Download stored PDF (auth) |
| GET    | `/api/v1/extract/excel/download?path=...` | Download Excel by path (auth) |
| GET    | `/health` | Health check |

---

## OCR flow (scanned PDFs)

1. **Detection** — `pypdf` checks if any page has extractable text; if none, the PDF is treated as scanned.
2. **Page images** — `pdf2image` (Poppler) converts one page at a time to images at 150 DPI to limit memory.
3. **OCR** — Tesseract (`pytesseract`) runs on each image; word-level text and bounding boxes are collected.
4. **Layout** — Words are turned into blocks (page, position) and merged with the same formatter used for text PDFs.
5. **Tables** — Still from pdfplumber (may be empty for image-only PDFs); any extracted tables are appended to the text passed to the LLM.
6. **Downstream** — Formatter builds text + hints; LLM returns JSON; Excel is generated as for text PDFs.

---

## Deployment (Render)

- **Use Docker** so Tesseract and Poppler are available (no buildpack support for these binaries).
- In Render: create a **Web Service** → **Environment**: Docker → **Root Directory**: `be` (so `be/Dockerfile` is used).
- Set all required env vars (`API_KEY`, Supabase, optional DB and email). For Postgres, prefer Supabase connection pooler (e.g. port **6543**) and `DATABASE_URL` with `?sslmode=require` if needed.
- **Email:** Resend is recommended; set `RESEND_API_KEY` and optionally `MAIL_FROM`. SMTP is often restricted on Render.
- **Cold starts:** Free tier may sleep after inactivity; first request can take ~30 s. Use `/health` to warm up before calling `/extract`.
- **Timeouts:** Extract uses long timeouts (e.g. 300 s for OCR); Render’s proxy may still close at ~30 s. For large scanned PDFs, consider a longer timeout or another host.

---

## Roadmap

- [ ] Configurable Pydantic schemas per `document_type` for strict validation of LLM output.
- [ ] Webhook or queue for async extraction of large documents.
- [ ] More document types (purchase orders, contracts) and field presets.
- [ ] Optional caching of extraction results by file hash.

---

## Contributing

1. Fork the repo and create a branch from `main`.
2. Install dev deps and run tests (see above).
3. Follow existing code style (FastAPI patterns, type hints).
4. Open a PR with a short description and reference any issue.

---

## License

See [LICENSE](LICENSE) in the repository root.
