"""
Test script to verify that py_mini_racer works in the packaged application.
This script should be run inside the packaged application environment.
"""
import sys
import os

print("Testing py_mini_racer in packaged application...")

try:
    from py_mini_racer import MiniRacer
    print("✓ MiniRacer imported successfully")
    
    # Test basic functionality
    ctx = MiniRacer()
    result = ctx.eval("1 + 1")
    print(f"✓ Basic evaluation works: 1 + 1 = {result}")
    
    print("All tests passed! py_mini_racer is working correctly.")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
except Exception as e:
    print(f"✗ Runtime error: {e}")

print("Test completed.")