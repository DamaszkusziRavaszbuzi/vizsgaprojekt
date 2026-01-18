#!/usr/bin/env python3
"""
run_app.py — bootstrapper that ensures a virtual environment exists,
installs required Python packages (including 'ollama'), and runs app.py
inside that environment.

Usage:
  - python run_app.py         # creates .venv (if needed), installs deps, runs app.py
  - python run_app.py --install-only   # create venv and install deps, then exit
  - python run_app.py --venv-dir <dir> # use custom venv directory
"""

import os
import sys
import subprocess
import argparse
import venv
import shutil

DEFAULT_VENV_DIR = ".venv"
REQUIRED_PACKAGES = [
    "ollama",
    "flask",
    "werkzeug",
]

def run(cmd, env=None):
    print("> " + " ".join(cmd))
    proc = subprocess.run(cmd, env=env)
    if proc.returncode != 0:
        raise SystemExit(f"Command failed with exit code {proc.returncode}")

def ensure_venv(venv_dir):
    if os.path.exists(venv_dir) and os.path.isdir(venv_dir):
        print(f"Using existing virtual environment: {venv_dir}")
        return
    print(f"Creating virtual environment at {venv_dir} ...")
    venv.create(venv_dir, with_pip=True)
    print("Virtual environment created.")

def python_in_venv(venv_dir):
    if os.name == "nt":
        return os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        return os.path.join(venv_dir, "bin", "python")

def pip_install(venv_python, packages):
    # Upgrade pip first
    run([venv_python, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    # Install packages
    cmd = [venv_python, "-m", "pip", "install"] + packages
    run(cmd)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--venv-dir", default=DEFAULT_VENV_DIR, help="Virtualenv directory")
    parser.add_argument("--install-only", action="store_true", help="Only create venv and install deps, do not run the app")
    parser.add_argument("--recreate", action="store_true", help="Remove existing venv and recreate it")
    args = parser.parse_args()

    venv_dir = args.venv_dir

    if args.recreate and os.path.exists(venv_dir):
        print(f"Removing existing venv at {venv_dir} ...")
        shutil.rmtree(venv_dir)

    ensure_venv(venv_dir)
    venv_python = python_in_venv(venv_dir)

    # Check that python in venv exists
    if not os.path.exists(venv_python):
        raise SystemExit(f"Virtualenv python not found at {venv_python}")

    try:
        pip_install(venv_python, REQUIRED_PACKAGES)
    except SystemExit as e:
        print("Package installation failed:", e)
        print("You may need to run the script with network access or fix the environment.")
        sys.exit(1)

    if args.install_only:
        print("Installation complete. Exiting (install-only).")
        return

    # Run the application using the venv python. We exec so that signals are delivered to the app.
    app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    if not os.path.exists(app_path):
        raise SystemExit(f"app.py not found at expected location: {app_path}")

    print("Starting app.py with venv python ...")
    os.execv(venv_python, [venv_python, app_path])

if __name__ == "__main__":
    main()
