"""Security threat models and compliance tooling for dfetch."""

import os
import sys

# Ensure the security package is importable when loaded by Sphinx directive
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)
