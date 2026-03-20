"""
Monkey patch to replace pkg_resources with importlib.resources in py_mini_racer.
This fixes the deprecation warning for pkg_resources.

Usage: Import this module before importing py_mini_racer
    from core.pkg_resources_patch import apply_patch
    apply_patch()
    
    from py_mini_racer import MiniRacer
"""

import sys
import os
from pathlib import Path
from typing import Optional


def _get_resource_path(package: str, resource: str) -> Optional[str]:
    """Get the path to a package resource using importlib.resources."""
    try:
        from importlib.resources import files
        from importlib.abc import Traversable
        
        traversable: Traversable = files(package)
        resource_path = traversable.joinpath(resource)
        
        if resource_path.exists():
            return str(resource_path)
    except (ImportError, AttributeError, TypeError):
        pass
    
    try:
        import importlib.resources as ir
        if hasattr(ir, 'path'):
            with ir.path(package, resource) as p:
                if p.exists():
                    return str(p)
    except (ImportError, AttributeError, TypeError, FileNotFoundError):
        pass
    
    return None


class PkgResourcesShim:
    """Shim for pkg_resources.resource_filename using importlib.resources."""
    
    @staticmethod
    def resource_filename(package: str, resource: str) -> str:
        """Return the path to a package resource."""
        path = _get_resource_path(package, resource)
        if path is not None:
            return path
        
        root_dir = os.path.dirname(os.path.abspath(__file__))
        fallback_path = os.path.join(root_dir, resource)
        if os.path.exists(fallback_path):
            return fallback_path
        
        raise FileNotFoundError(
            f"Cannot find resource {resource!r} in package {package!r}"
        )


def apply_patch():
    """Apply the monkey patch to replace pkg_resources."""
    if 'pkg_resources' not in sys.modules:
        sys.modules['pkg_resources'] = PkgResourcesShim()
    
    import py_mini_racer.py_mini_racer as pmr
    if hasattr(pmr, 'pkg_resources') and pmr.pkg_resources is not None:
        pmr.pkg_resources = PkgResourcesShim()


def remove_patch():
    """Remove the monkey patch (restore original behavior)."""
    if 'pkg_resources' in sys.modules:
        if isinstance(sys.modules['pkg_resources'], PkgResourcesShim):
            del sys.modules['pkg_resources']
