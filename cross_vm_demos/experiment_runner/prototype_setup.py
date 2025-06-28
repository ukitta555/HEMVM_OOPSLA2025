"""
Dynamic prototype folder setup utility for cross_vm_demos package.
This module provides a clean way to find the prototype folder (MoviEth or aptos-core)
without hardcoding absolute paths.
"""

import sys
from pathlib import Path
from enum import Enum


class PrototypeType(Enum):
    """Enum for different types of prototype folders."""
    MOVIETH = "MoviEth"
    APTOS_CORE = "aptos-core"


def find_prototype_folder(prototype_type: PrototypeType) -> Path:
    """
    Find the prototype folder dynamically based on the cross_vm_demos structure.
    
    This function finds the prototype folder (MoviEth or aptos-core) relative to the 
    cross_vm_demos directory structure. It works regardless of where the script is 
    located within the cross_vm_demos package structure.
    
    Args:
        prototype_type: The type of prototype folder to find (MoviEth or aptos-core)
    
    Returns:
        Path: Path object pointing to the prototype folder
        
    Raises:
        FileNotFoundError: If the prototype folder cannot be found
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
            else:
                raise FileNotFoundError("Could not find cross_vm_demos directory")
    
    # Now look for the prototype folder at the same level as cross_vm_demos
    cross_vm_demos_parent = cross_vm_demos_path.parent
    
    # Look for the prototype folder
    prototype_folder = cross_vm_demos_parent / prototype_type.value
    
    if not prototype_folder.exists():
        raise FileNotFoundError(
            f"Prototype folder '{prototype_type.value}' not found at {prototype_folder}. "
            f"Expected location: {cross_vm_demos_parent}/"
        )
    
    print(f"Found prototype folder: {prototype_folder}")
    return prototype_folder


def get_movieth_folder() -> Path:
    """
    Get the path to the MoviEth prototype folder.
    
    Returns:
        Path: Path object pointing to the MoviEth directory
    """
    return find_prototype_folder(PrototypeType.MOVIETH)


def get_aptos_core_folder() -> Path:
    """
    Get the path to the aptos-core prototype folder.
    
    Returns:
        Path: Path object pointing to the aptos-core directory
    """
    return find_prototype_folder(PrototypeType.APTOS_CORE)


# Convenience function for backward compatibility
def setup_prototype_folder(prototype_type: PrototypeType) -> Path:
    """
    Setup and return the prototype folder path.
    
    This is a convenience function that provides the same functionality as 
    find_prototype_folder but with a more descriptive name.
    
    Args:
        prototype_type: The type of prototype folder to find (MoviEth or aptos-core)
    
    Returns:
        Path: Path object pointing to the prototype folder
    """
    return find_prototype_folder(prototype_type)


# Example usage and testing
if __name__ == "__main__":
    try:
        movieth_path = get_movieth_folder()
        print(f"MoviEth folder: {movieth_path}")
        
        aptos_core_path = get_aptos_core_folder()
        print(f"Aptos-core folder: {aptos_core_path}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure the prototype folders are located at the same level as cross_vm_demos") 