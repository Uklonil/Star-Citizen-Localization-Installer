from __future__ import annotations

import sys

from blueprint_mission_review import main


if __name__ == "__main__":
    raise SystemExit(main(["--mode", "shortlist", *sys.argv[1:]]))
