"""Path utilities for handling development and PyInstaller environments.

This module provides unified path calculation functions that work correctly
in both development and packaged (PyInstaller) environments.

Usage:
    from core.paths import get_base_path, get_data_path
    
    base_path = get_base_path()  # For code/templates (in _MEIPASS when packaged)
    data_path = get_data_path()  # For persistent data (cache, models, reports)
"""
from pathlib import Path
import sys


def get_base_path() -> Path:
    """Get the base path for the application (for code/modules).
    
    In development: Returns the python-api directory
    In PyInstaller: Returns the _MEIPASS temporary directory
    
    Use this for:
    - Loading Python modules
    - Reading template files
    - Accessing bundled resources
    
    Returns:
        Path to the application base directory
    """
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


def get_data_path() -> Path:
    """Get the data path for persistent data (cache, models, reports).
    
    In development: Returns the python-api directory
    In PyInstaller: Returns the directory where the exe is located
    
    This ensures cache and other data persist across runs.
    
    Use this for:
    - Cache files (datasets/cache)
    - Model files (datasets/models)
    - Report files (reports)
    - Any user data that should persist
    
    Returns:
        Path to the data directory
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def ensure_data_directories(base_dir: Path | None = None) -> dict[str, Path]:
    """Ensure all required data directories exist.
    
    Args:
        base_dir: Base directory for data (defaults to get_data_path())
        
    Returns:
        Dictionary with paths to created directories
    """
    base = base_dir or get_data_path()
    
    directories = {
        "cache": base / "datasets" / "cache",
        "models": base / "datasets" / "models",
        "snapshots": base / "datasets" / "snapshots",
        "reports": base / "reports",
        "images": base / "reports" / "images",
    }
    
    for dir_path in directories.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return directories
