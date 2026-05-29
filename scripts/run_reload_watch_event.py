import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.market_intelligence.reload_watch_manual_cli import main


if __name__ == "__main__":
    raise SystemExit(main())
