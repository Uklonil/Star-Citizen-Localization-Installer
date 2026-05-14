from __future__ import annotations

import sys

from blueprint_reward_pool_review import main


if __name__ == "__main__":
    raise SystemExit(main(["--mode", "discover", *sys.argv[1:]]))
