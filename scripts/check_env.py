#!/usr/bin/env python3
import sys
import subprocess
import importlib.util

def check_package(package_name):
    """Check if a Python package is installed."""
    spec = importlib.util.find_spec(package_name)
    return spec is not None

def check_command(command_name):
    """Check if a shell command exists."""
    try:
        subprocess.run([command_name, "--version"], capture_output=True, check=False)
        return True
    except FileNotFoundError:
        return False

def run_checks():
    """Verify core dependencies for Nova Rules validation and testing."""
    # python packages
    required_pkgs = ["nova", "colorama", "yaml"]
    # shell commands
    required_cmds = ["yamllint"]
    
    missing = []
    
    print("--- Environment Check ---")
    for pkg in required_pkgs:
        if check_package(pkg):
            print(f"[OK] {pkg} (Python package)")
        else:
            print(f"[MISSING] {pkg} (Python package)")
            missing.append(pkg)
            
    for cmd in required_cmds:
        if check_command(cmd):
            print(f"[OK] {cmd} (Command line tool)")
        else:
            print(f"[MISSING] {cmd} (Command line tool)")
            missing.append(cmd)
            
    if missing:
        print("\nDependencies missing! Please run:")
        print("pip install nova-hunting yamllint")
        return False
        
    print("\nAll core dependencies found.")
    return True

if __name__ == "__main__":
    if not run_checks():
        sys.exit(1)
