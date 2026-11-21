# PROHEAT Accounting Entry — app context

Updated: 21 November 2026. This file summarizes the current repository for future development sessions. See `docs/DEVELOPMENT_PROGRESS.md` for the change history and verification notes.

## Purpose and user workflow

This is a private, local invoice extraction app. The user signs in, uploads up to 100 PDF/JPEG/PNG invoices in a batch, waits for background processing, and downloads an XLSX file. The workbook contains `FACTURES`, `LIGNES`, and `ANOMALIES`. Missing or uncertain values and inconsistent totals are marked on the affected Excel cells with red fill and comments. Users should not have to correct every invoice inside the app. Existing batches can be reprocessed without deleting their earlier records. The navigation contains Tableau de bord, Traitement par lots, Référentiel réglementaire, Journal d'audit, and Paramètres.

## Runtime and data

- FastAPI/Python backend: `backend/main.py`; frontend: `frontend/index.html`, `frontend/app.js`, and `frontend/styles.css`.
- Docker Compose runs the app at `http://localhost:8081` and PostgreSQL on an internal network. `database` and `documents` are persistent named volumes. Do not run `docker compose down -v` or reset the database for ordinary development.
- `backend/main.py` owns the SQLAlchemy models, login/session routes, batch worker, document storage, and API endpoints. A single app process and its background worker are assumed.
- The original files are stored in the `documents` volume under generated IDs; extracted fields, batches, issues, users, and audit events are in PostgreSQL.
- Extraction and OCR use PyMuPDF and local Tesseract. Invoice contents are not sent to an external AI service.

## Extraction and exports

- `backend/extraction.py` handles labelled text fields, some line layouts, and arithmetic validation.
- `backend/layout_extraction.py` adds position-aware PDF totals and item rows, two-digit invoice dates, issuer ICE selection when buyer and seller ICEs differ, and local OCR of image headers. A supplier name read only from a logo is marked `ocr_uncertain` and flagged in Excel. Its spelling is not silently treated as verified.
- `backend/batch_validation.py` reports missing or uncertain fields, duplicate references, and inconsistent totals. No accounting rule is verified or active; the app does not produce validated accounting entries.
- `backend/invoice_workbook.py` generates the invoice-data XLSX and independently reopens it to check its contents and annotations. `backend/batch_report.py` generates the separate exception report.
- An exact duplicate is still extracted and reported with its earlier document or batch reference. Reprocessing creates a new batch and preserves history.
- The older direct upload API still exists, although the visible upload flow uses batches.

## Current verification and limitations

- The full available suite last passed: 20 tests via Docker. Synthetic tests cover batch duplicates, workbook annotations, extraction, and a position-aware PDF with fictional values.
- A real invoice supplied by the user was used locally to validate extraction: 17 line items and consistent HT/TVA/TTC were found. Its logo OCR spelling remains uncertain. The real PDF is not part of the repository or tests.
- One example does not train universal invoice recognition. Other invoice designs, poor scans, handwriting, tables spanning pages, and unusual tax layouts need more synthetic fixtures and validation. Do not fabricate unreadable values, supplier identities, accounting rules, or account mappings.
- README and parts of the historical progress document contain older MVP language; verify current behavior in code and tests before relying on them.

## Useful commands (Windows PowerShell)

```powershell
docker compose up -d --build
docker compose ps
docker compose run --rm --no-deps -v "${PWD}/backend:/work/backend:ro" -v "${PWD}/tests:/work/tests:ro" -e TEST_BACKEND_DIR=/work/backend app python -m unittest discover -s /work/tests -q
```

After changing extraction code, reprocess an existing batch to update its stored fields, then download a fresh XLSX. The export route also re-extracts from retained files. Keep all real invoices, secrets, and generated workbooks out of Git.
