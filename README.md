# Accounts Payable

**[Live demo →](https://accountspayable.streamlit.app/)**

An AI-powered invoice processing and accounts payable reporting tool built for a professional hockey team's finance operations. The deployed demo comes pre-loaded with a small set of realistic sample invoices, so you can explore every page immediately without uploading anything.

## What it does

- **Upload** PDF or image invoices → automatic field and line-item extraction via the OpenAI API, with a regex-based fallback parser if the model call fails
- **OCR fallback** for scanned or image-based invoices with no embedded text, via PyMuPDF + Tesseract
- **Manual review and approval** before anything is saved — original document and extracted data shown side by side, fully editable
- **Edit or delete** any saved invoice at any time
- **SQLite-backed ledger** with full-text search across vendor, invoice number, and purchased items
- **Automatic duplicate-invoice detection**
- **Insights** — ask natural-language questions ("who do we spend the most with?", "what invoices need review?"), explore interactive spend charts (vendor concentration, monthly trend, invoice amount distribution, validation status), and drill into individual vendors
- **Executive Report** — one-click AI-generated CFO-style narrative report, plus vendor/product spend-concentration charts, a risk assessment, and management recommendations
- **Excel export** — a formatted, multi-sheet workbook (invoices, line items, vendor summary) for offline use

## Tech stack

Python · Streamlit · OpenAI API · SQLite · PyMuPDF (PDF parsing + OCR) · Altair (charts) · openpyxl (Excel export)

## Notes

- The deployed demo's uploaded files and database reset on redeploy or after the app sleeps from inactivity (Streamlit Community Cloud's filesystem is ephemeral by design) — sample data reseeds automatically so it's never empty.
- Real invoices and financial data should never be committed to this repository — synthetic or properly redacted documents only. See `.gitignore`.

## Processing pipeline

1. Validate the uploaded file
2. Extract embedded PDF text (or run OCR if none is found)
3. Extract structured invoice fields and line items via AI
4. Validate extracted values and flag mismatches for review
5. Store in the invoice database after manual approval
6. Surface insights, an AI-generated executive report, and Excel export from the stored data
