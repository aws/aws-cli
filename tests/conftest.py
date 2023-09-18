"""Configure pytest."""
import pathlib
import sys

parent = pathlib.Path(__file__).parent.parent.absolute()
SOURCES_ROOT = parent / "src"
if SOURCES_ROOT.is_dir() and str(SOURCES_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCES_ROOT))

if str(parent) not in sys.path:
    sys.path.insert(0, str(parent))
