from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).parent
LOCAL_PACKAGES = ROOT_DIR / ".packages"

if LOCAL_PACKAGES.exists():
    sys.path.insert(0, str(LOCAL_PACKAGES))

from streamlit.web.cli import main  # noqa: E402


if __name__ == "__main__":
    sys.argv = [
        "streamlit",
        "run",
        str(ROOT_DIR / "app.py"),
        *sys.argv[1:],
    ]
    raise SystemExit(main())
