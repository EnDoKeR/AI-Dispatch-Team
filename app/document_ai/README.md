# Document AI Contracts

This package contains lightweight contracts for future document processing.

It does not implement PDF parsing, OCR, Vision AI, external APIs, case creation,
Telegram upload handling, or event writing. Contracts here should remain safe to
import from tests and reports without touching private documents.

Current contracts:

- `document_types.py`
- `document_record.py`
- `pdf_triage_contract.py`
- `extraction_artifacts.py`
- `ratecon_schema.py`
