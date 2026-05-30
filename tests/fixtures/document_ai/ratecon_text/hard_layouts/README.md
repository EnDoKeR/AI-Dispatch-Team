# Fake Hard-Layout RateCon Fixtures

These files are fake/anonymized resolver-hardening fixtures.

Rules:

- no private RateCon text;
- no real broker names;
- no real MC numbers;
- no real customer, carrier, or driver data;
- no phone numbers, emails, real addresses, or private reference numbers;
- no private local file paths;
- intended for candidate/template/resolver tests only;
- not a production accuracy benchmark.

The fixtures may use page markers such as:

```text
--- PAGE 1 ---
--- PAGE 2 ---
```

The fixture loader treats those markers as fake page boundaries when building
text artifacts for candidate extraction.
