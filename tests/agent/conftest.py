import sys
from pathlib import Path

# Ensure agent/ is first in path for agent tests
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "agent"))
