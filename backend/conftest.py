import os
import sys
import pathlib

# Automatically insert backend directory into sys.path for pytest
backend_dir = pathlib.Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
