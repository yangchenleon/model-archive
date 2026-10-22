import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.normalize_products import main

if __name__ == "__main__":
    sys.exit(main())
