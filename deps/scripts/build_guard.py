"""CI guard shared by the expensive dependency builders.

Every builder calls guard() right before doing expensive work. Two
environment variables drive it, both set only by CI:

- AWSCLI_FORBID_EXPENSIVE_BUILDS: when set, the builder exits immediately
  with a loud error. CI sets this for every product-phase invocation, so a
  cache regression that reaches a dependency builder fails in seconds
  instead of hiding inside a long successful build.
- AWSCLI_BUILDER_MARKER_DIR: when set, the builder appends an invocation
  marker file under this directory. CI uses the markers to classify a run
  as warm (dependency snapshot restored, zero builders ran) and to decide
  whether to save a new snapshot generation.

Local builds set neither variable and are unaffected: a plain `cargo xtask deps`
may regenerate anything that is missing.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

FORBID_ENV = "AWSCLI_FORBID_EXPENSIVE_BUILDS"
MARKER_DIR_ENV = "AWSCLI_BUILDER_MARKER_DIR"


def guard(builder: str) -> None:
    if os.environ.get(FORBID_ENV):
        sys.exit(
            f"{builder}: expensive dependency builds are forbidden in this "
            f"build phase ({FORBID_ENV} is set). A dependency output that "
            "should have been reused from the build cache was about to be "
            "rebuilt; treat this as a cache regression, not a build failure."
        )
    marker_dir = os.environ.get(MARKER_DIR_ENV)
    if marker_dir:
        directory = Path(marker_dir)
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / builder).open("a", encoding="utf-8") as marker:
            marker.write("ran\n")
