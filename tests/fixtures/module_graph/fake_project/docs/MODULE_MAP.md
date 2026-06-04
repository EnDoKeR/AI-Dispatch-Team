# Fixture Module Map

| module_path | package_area | owner_layer | status | entrypoints | imported_by_summary | imports_summary | remove_after | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `main.py` | root | fixture runtime | active | direct | fixture | app active module |  | Fixture production entrypoint. |
| `app/active.py` | fixture_app | fixture core | active | library | main and script | deprecated and experimental fixture modules |  | Intentional risk references for tests. |
| `app/deprecated_mod.py` | fixture_app | fixture legacy | deprecated | library | active module | none | after fixture proof | Deprecated fixture module. |
| `app/experimental_mod.py` | fixture_app | fixture experiment | experimental | library | active module | none | after fixture proof | Experimental fixture module. |
| `app/cycle_a.py` | fixture_app | fixture cycle | active | library | cycle b | cycle b |  | Cycle fixture. |
| `app/cycle_b.py` | fixture_app | fixture cycle | active | library | cycle a | cycle a |  | Cycle fixture. |
| `scripts/run_cli.py` | fixture_scripts | fixture CLI | active | CLI | manual | app active module |  | Active CLI fixture. |
| `scripts/script_only.py` | fixture_scripts | fixture CLI | local_only | CLI | manual | none |  | Script-only fixture. |
| `tests/sample_test_module.py` | fixture_tests | fixture tests | test_only | unittest | unittest | app active module |  | Test fixture. |
| `tests/helper_only.py` | fixture_tests | fixture tests | test_only | helper | tests | none |  | Test-only helper fixture. |
| `app/missing_module.py` | fixture_app | fixture missing | active | library | none | none |  | Listed missing fixture row. |
