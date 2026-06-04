from pathlib import Path


Path("module_graph_should_not_exist.txt").write_text("imported", encoding="utf-8")
VALUE = "fixture-side-effect"
