#!/usr/bin/env python
"""Launch the C-Suite Executive GUI."""

import sys
import os
from pathlib import Path

# Get the c-suite root
csuite_root = Path(__file__).parent.parent

# Set working directory
os.chdir(csuite_root)

# Fix Qt rendering issues
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

# Remove any conflicting packages from sys.path
sys.path = [p for p in sys.path if 'Sentinel' not in p]

# Add csuite src to path
sys.path.insert(0, str(csuite_root / "src"))

# Launch the GUI
from csuite.gui import run
run()
