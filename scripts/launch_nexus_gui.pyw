#!/usr/bin/env python
"""Launch the Nexus Intelligence GUI from C-Suite."""

import sys
import os
from pathlib import Path

# Get the c-suite root and nexus source paths
csuite_root = Path(__file__).parent.parent
nexus_src = csuite_root / "src" / "nexus" / "src"

# Set working directory
os.chdir(csuite_root)

# Fix Qt rendering issues
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

# Remove any conflicting nexus from sys.modules
mods_to_remove = [k for k in sys.modules if k == 'nexus' or k.startswith('nexus.')]
for mod in mods_to_remove:
    del sys.modules[mod]

# Remove Sentinel path from sys.path to avoid conflicts
sys.path = [p for p in sys.path if 'Sentinel' not in p]

# Add the correct paths at the very beginning
sys.path.insert(0, str(nexus_src))
sys.path.insert(0, str(csuite_root / "src"))

# Now import and run
from nexus.gui.app import run
run()
