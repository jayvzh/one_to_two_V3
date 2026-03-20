"""
Test script to verify the pkg_resources patch works correctly.
"""

import sys
import os
import warnings

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Testing pkg_resources patch...")

warnings.filterwarnings("error", message="pkg_resources is deprecated")

try:
    from core.pkg_resources_patch import apply_patch
    apply_patch()
    print("✓ Patch applied successfully")
except Exception as e:
    print(f"✗ Failed to apply patch: {e}")
    sys.exit(1)

try:
    from py_mini_racer import MiniRacer
    print("✓ MiniRacer imported without warnings")
except UserWarning as w:
    print(f"✗ Warning still present: {w}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

try:
    ctx = MiniRacer()
    result = ctx.eval("1 + 1")
    print(f"✓ Basic evaluation works: 1 + 1 = {result}")
except Exception as e:
    print(f"✗ Runtime error: {e}")
    sys.exit(1)

print("\nAll tests passed! The patch works correctly.")
