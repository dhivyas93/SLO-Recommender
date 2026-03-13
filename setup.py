#!/usr/bin/env python3
"""
SLO Recommendation System - Local Setup Script

This script sets up Ollama and downloads necessary models for the demo.
Works on macOS, Linux, and Windows.

Usage:
    python setup.py
"""

import os
import sys
import subprocess
import platform
import time
import json
from pathlib import Path
from typing import Tuple, Optional


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def disable():
        """Disable colors on Windows or when not supported."""
        Colors.HEADER = ''
        Colors.BLUE = ''
        Colors.CYAN = ''
        Colors.GREEN = ''
        Colors.YELLOW = ''
        Colors.RED = ''
        Colors.ENDC = ''
        Colors.BOLD = ''
        Colors.UNDERLINE = ''


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.ENDC}\n")


def print_section(text: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{text}{Colors.ENDC}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓{Colors.ENDC} {text}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗{Colors.ENDC} {text}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.ENDC} {text}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ{Colors.ENDC} {text}")


def command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    try:
        subprocess.run(
            ["which" if sys.platform != "win32" else "where", command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def run_command(command: list, description: str = "") -> Tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def install_ollama() -> bool:
    """Install Ollama based on OS."""
    os_type = platform.system()
    print_section(f"📦 Installing Ollama for {os_type}")

    if os_type == "Darwin":  # macOS
        if command_exists("brew"):
            print_info("Using Homebrew to install Ollama...")
            success, output = run_command(["brew", "install", "ollama"])
            if success:
                print_success("Ollama installed via Homebrew")
                return True
            else:
                print_warning("Homebrew installation failed, trying direct download...")

        print_info("Downloading Ollama installer from ollama.ai...")
        success, output = run_command([
            "curl", "-fsSL", "https://ollama.ai/install.sh", "|", "sh"
        ])
        if success:
            print_success("Ollama installed successfully")
            return True

    elif os_type == "Linux":
        print_info("Downloading Ollama installer for Linux...")
        success, output = run_command([
            "curl", "-fsSL", "https://ollama.ai/install.sh", "|", "sh"
        ])
        if success:
            print_success("Ollama installed successfully")
            return True

    elif os_type == "Windows":
        print_error("Ollama installation on Windows requires manual download")
        print_info("Please download and install from: https://ollama.ai")
        print_info("After installation, run this script again")
        return False

    print_error("Failed to install Ollama")
    return False


def check_ollama() -> bool:
    """Check if Ollama is installed."""
    if command_exists("ollama"):
        print_success("Ollama is already installed")
        try:
            success, version = run_command(["ollama", "--version"])
            if success:
                print_info(f"Version: {version.strip()}")
        except:
            pass
        return True
    return False


def check_python() -> bool:
    """Check if Python 3.8+ is installed."""
    print_section("📋 Checking Python dependencies")

    if not command_exists("python3") and not command_exists("python"):
        print_error("Python 3 is required but not installed")
        print_info("Please install Python 3.8+ from https://www.python.org")
        return False

    try:
        result = subprocess.run(
            ["python3", "--version"] if command_exists("python3") else ["python", "--version"],
            capture_output=True,
            text=True
        )
        version = result.stdout + result.stderr
        print_success(f"Python found: {version.strip()}")
    except:
        print_error("Failed to check Python version")
        return False

    if not command_exists("pip3") and not command_exists("pip"):
        print_error("pip is required but not installed")
        return False

    print_success("pip found")
    return True


def install_python_dependencies() -> bool:
    """Install Python dependencies from requirements.txt."""
    print_section("📦 Installing Python dependencies")

    if not Path("requirements.txt").exists():
        print_warning("requirements.txt not found, skipping Python dependencies")
        return True

    pip_cmd = "pip3" if command_exists("pip3") else "pip"
    print_info(f"Using {pip_cmd} to install dependencies...")

    success, output = run_command([pip_cmd, "install", "-r", "requirements.txt"])
    if success:
        print_success("Python dependencies installed")
        return True
    else:
        print_error("Failed to install Python dependencies")
        print_info(f"Output: {output}")
        return False


def is_ollama_running() -> bool:
    """Check if Ollama server is running."""
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except:
        return False


def start_ollama_server() -> bool:
    """Start Ollama server in background."""
    print_section("🤖 Starting Ollama server")

    if is_ollama_running():
        print_success("Ollama server is already running")
        return True

    print_info("Starting Ollama server...")

    try:
        if platform.system() == "Windows":
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print_info("Waiting for Ollama server to be ready...")
        for i in range(30):
            time.sleep(1)
            if is_ollama_running():
                print_success("Ollama server is ready")
                return True

        print_error("Ollama server failed to start")
        return False
    except Exception as e:
        print_error(f"Failed to start Ollama server: {e}")
        return False


def pull_model(model: str, description: str) -> bool:
    """Pull a model from Ollama."""
    print_info(f"Pulling {model} ({description})...")

    # Check if model already exists
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if model in result.stdout:
            print_success(f"{model} is already available")
            return True
    except:
        pass

    print_info(f"Downloading {model} (this may take a few minutes)...")

    success, output = run_command(["ollama", "pull", model])
    if success:
        print_success(f"{model} downloaded successfully")
        return True
    else:
        print_warning(f"Failed to download {model}")
        print_info(f"You can download it manually later with: ollama pull {model}")
        return False


def setup_models() -> bool:
    """Download recommended models."""
    print_section("🤖 Setting up Ollama models")

    if not is_ollama_running():
        print_error("Ollama server is not running")
        print_info("Please start Ollama with: ollama serve")
        return False

    print_info("Downloading recommended models...")
    print()

    # Pull models
    models = [
        ("orca-mini", "Fast, lightweight model (1.3GB)"),
        ("mistral", "Balanced model (4.4GB)"),
    ]

    success_count = 0
    for model, description in models:
        if pull_model(model, description):
            success_count += 1
        print()

    if success_count > 0:
        print_success(f"Model setup complete ({success_count}/{len(models)} models)")
        return True
    else:
        print_warning("No models were downloaded")
        return False


def main():
    """Main setup function."""
    # Disable colors on Windows if not supported
    if platform.system() == "Windows" and not os.environ.get("TERM"):
        Colors.disable()

    print_header("SLO RECOMMENDATION SYSTEM - SETUP")

    os_type = platform.system()
    print_info(f"Detected OS: {os_type}")
    print()

    # Step 1: Check/Install Ollama
    if not check_ollama():
        print_warning("Ollama is not installed")
        if not install_ollama():
            print_error("Failed to install Ollama")
            print_info("Please install manually from https://ollama.ai and try again")
            return False

    # Step 2: Check Python
    if not check_python():
        print_error("Python setup failed")
        return False

    # Step 3: Install Python dependencies
    if not install_python_dependencies():
        print_warning("Some Python dependencies may not be installed")

    # Step 4: Start Ollama server
    if not start_ollama_server():
        print_warning("Could not start Ollama server automatically")
        print_info("Please start it manually with: ollama serve")
        print_info("Then run this script again")
        return False

    # Step 5: Setup models
    if not setup_models():
        print_warning("Model setup incomplete")

    # Success!
    print_header("SETUP COMPLETE! 🎉")

    print(f"{Colors.GREEN}Next steps:{Colors.ENDC}")
    print(f"  1. Keep Ollama running: {Colors.BOLD}ollama serve{Colors.ENDC}")
    print(f"  2. In another terminal, run the demo: {Colors.BOLD}python demo.py{Colors.ENDC}")
    print()
    print(f"{Colors.BLUE}To stop Ollama later:{Colors.ENDC}")
    if platform.system() == "Windows":
        print(f"  {Colors.BOLD}taskkill /IM ollama.exe /F{Colors.ENDC}")
    else:
        print(f"  {Colors.BOLD}killall ollama{Colors.ENDC}")
    print()
    print(f"{Colors.BLUE}For more information, see SETUP.md{Colors.ENDC}")
    print()

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_warning("\nSetup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
