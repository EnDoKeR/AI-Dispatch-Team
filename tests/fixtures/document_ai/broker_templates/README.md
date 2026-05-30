# Fake Broker Template Fixtures

These broker templates are fake/anonymized and are used only for document
extraction tests.

Rules:

- no real broker names;
- no real MC numbers;
- no private customer, driver, carrier, phone, email, or address data;
- templates describe document layout and extraction labels only;
- BrokerTemplate is not BrokerProfile or broker memory;
- templates must not encode payment history, factoring status, business risk, or
  dispatch recommendations.

Fixture intent:

- `alpha_freight_mock_v1.json`: clean digital-style layout.
- `northstar_logistics_mock_v1.json`: alternate vocabulary.
- `tablelane_transport_mock_v1.json`: table-heavy / stop-table vocabulary.
- `conflict_mock_v1.json`: intentionally overlaps another fake template for
  conflict tests.
