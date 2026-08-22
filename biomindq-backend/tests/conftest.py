import sys
from pathlib import Path

# Add app directory to PYTHONPATH for tests
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))
