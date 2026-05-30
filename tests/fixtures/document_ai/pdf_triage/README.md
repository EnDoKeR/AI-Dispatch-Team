# Safe PDF Triage Fixtures

PDF triage tests must not use private RateCons or extracted private text.

Fixture types:

1. `digital_text_ratecon_like.pdf`
   - generated during tests in a temp directory;
   - fake broker/customer values only;
   - fake rate, stops, equipment, dates, commodity, and weight;
   - no real private data.

2. `image_like_or_empty_text.pdf`
   - generated during tests as a valid PDF with an empty text stream when
     practical;
   - represents the `EMPTY_TEXT` class without committing scanned private docs;
   - no OCR is run.

3. `broken_or_invalid.pdf`
   - generated during tests from intentionally invalid bytes;
   - used to verify safe broken/unreadable handling.

4. `mixed_pdf_like`
   - simulated by unit tests using page profiles or generated temp PDFs;
   - checked-in binary fixtures are not required.

Policy:

- do not commit private PDFs;
- do not commit extracted private text;
- do not create fixtures from private documents;
- prefer temp-generated fake PDFs or test doubles;
- keep all fixture text fake and anonymized.
