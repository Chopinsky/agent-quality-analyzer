import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[0] / ".." / "skills" / "agent-complexity-analyzer" / "scripts"
sys.path.insert(0, str(SRC))
