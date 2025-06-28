"""
Dynamic path setup utility for cross_vm_demos package.
This module provides a clean way to add the cross_vm_demos directory to Python path
without hardcoding absolute paths.
"""

import sys
from pathlib import Path


def setup_cross_vm_demos_path():
    """
    Add the cross_vm_demos directory to Python path dynamically.
    
    This function finds the cross_vm_demos directory relative to the calling script
    and adds it to sys.path. It works regardless of where the script is located
    within the cross_vm_demos package structure.
    
    Usage:
        from path_setup import setup_cross_vm_demos_path
        setup_cross_vm_demos_path()
        
        # Now you can import from cross_vm_demos modules
        from experiment_runner.funding_utils import ...
        from utils import ...
    """
    # Get the directory of the calling script
    caller_file = Path(sys._getframe(1).f_code.co_filename)
    
    # Find the cross_vm_demos directory by walking up the directory tree
    current_dir = caller_file.parent
    while current_dir != current_dir.parent:  # Stop at root
        if (current_dir / "cross_vm_demos").exists() or current_dir.name == "cross_vm_demos":
            # Found the cross_vm_demos directory
            cross_vm_demos_path = current_dir if current_dir.name == "cross_vm_demos" else current_dir / "cross_vm_demos"
            break
        current_dir = current_dir.parent
    else:
        # Fallback: assume we're already in cross_vm_demos or its subdirectory
        # Walk up until we find a directory with __init__.py (indicating it's a Python package)
        current_dir = caller_file.parent
        while current_dir != current_dir.parent:
            if (current_dir / "__init__.py").exists():
                cross_vm_demos_path = current_dir
                break
            current_dir = current_dir.parent
        else:
            # Last resort: use the parent of the script's directory
            if caller_file.parent.parent.parent.name == "cross_vm_demos":
                cross_vm_demos_path = caller_file.parent.parent.parent
            elif caller_file.parent.parent.name == "cross_vm_demos":
                cross_vm_demos_path = caller_file.parent.parent
    
    # Add to Python path if not already there
    cross_vm_demos_path_str = str(cross_vm_demos_path.absolute())
    if cross_vm_demos_path_str not in sys.path:
        sys.path.insert(1, cross_vm_demos_path_str)
        print(f"Added to Python path: {cross_vm_demos_path_str}")
    
    return cross_vm_demos_path


def get_cross_vm_demos_path():
    """
    Get the path to the cross_vm_demos directory without modifying sys.path.
    
    Returns:
        Path: Path object pointing to the cross_vm_demos directory
    """
    # Get the directory of the calling script
    caller_file = Path(sys._getframe(1).f_code.co_filename)
    
    # Find the cross_vm_demos directory by walking up the directory tree
    current_dir = caller_file.parent
    while current_dir != current_dir.parent:  # Stop at root
        if (current_dir / "cross_vm_demos").exists() or current_dir.name == "cross_vm_demos":
            # Found the cross_vm_demos directory
            return current_dir if current_dir.name == "cross_vm_demos" else current_dir / "cross_vm_demos"
        current_dir = current_dir.parent
    
    # Fallback: assume we're already in cross_vm_demos or its subdirectory
    current_dir = caller_file.parent
    while current_dir != current_dir.parent:
        if (current_dir / "__init__.py").exists():
            return current_dir
        current_dir = current_dir.parent
    
    # Last resort: use the parent of the script's directory
    return caller_file.parent.parent.parent


# Auto-setup when imported (optional)
if __name__ != "__main__":
    setup_cross_vm_demos_path()