#!/usr/bin/env python3
"""
Example script demonstrating how to use the prototype_setup utility.
This script shows how to replace hardcoded paths with dynamic path resolution.
"""

from pathlib import Path
from prototype_setup import get_movieth_folder, get_aptos_core_folder, PrototypeType, find_prototype_folder

def main():
    """Demonstrate the usage of the prototype setup utility."""
    
    print("=== Prototype Setup Utility Example ===\n")
    
    try:
        # Method 1: Using convenience functions
        print("1. Using convenience functions:")
        movieth_path = get_movieth_folder()
        print(f"   MoviEth folder: {movieth_path}")
        
        aptos_core_path = get_aptos_core_folder()
        print(f"   Aptos-core folder: {aptos_core_path}")
        
        # Method 2: Using the generic function with enum
        print("\n2. Using generic function with enum:")
        movieth_path_2 = find_prototype_folder(PrototypeType.MOVIETH)
        print(f"   MoviEth folder: {movieth_path_2}")
        
        aptos_core_path_2 = find_prototype_folder(PrototypeType.APTOS_CORE)
        print(f"   Aptos-core folder: {aptos_core_path_2}")
        
        # Verify the paths are the same
        print(f"\n3. Verification:")
        print(f"   MoviEth paths match: {movieth_path == movieth_path_2}")
        print(f"   Aptos-core paths match: {aptos_core_path == aptos_core_path_2}")
        
        # Show how to use in a real scenario
        print(f"\n4. Real usage example:")
        print(f"   # Instead of:")
        print(f"   # prototype_folder = Path('/home/fanlgrp/Projects/MovexEther/MoviEth')")
        print(f"   # Use:")
        print(f"   # from prototype_setup import get_movieth_folder")
        print(f"   # prototype_folder = get_movieth_folder()")
        
        # Demonstrate path operations
        print(f"\n5. Path operations:")
        api_src_path = movieth_path / "api" / "src"
        print(f"   API src path: {api_src_path}")
        print(f"   API src exists: {api_src_path.exists()}")
        
        ethrpc_path = movieth_path / "api" / "ethrpc" / "src" / "impls"
        print(f"   ETHRPC impls path: {ethrpc_path}")
        print(f"   ETHRPC impls exists: {ethrpc_path.exists()}")
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nMake sure the prototype folders are located at the same level as cross_vm_demos:")
        print("   MovexEther/")
        print("   ├── cross_vm_demos/")
        print("   ├── MoviEth/")
        print("   └── aptos-core/")
        
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main() 