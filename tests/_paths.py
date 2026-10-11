import sys

sys.dont_write_bytecode = True
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "topmind-research"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
for p in (SKILL / "scripts", ROOT / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
