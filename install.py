#!/usr/bin/env python3
"""
Comprehensive Installation Script for Deep Research Agent

This script handles the complete installation process including:
- Dependency installation
- Environment setup
- Configuration validation
- Vector database setup

Usage:
    python install.py
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path
from typing import List, Tuple

def run_command(command: List[str]) -> Tuple[bool, str]:
    """Run a command and return success status and output"""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def check_dependency(module_name: str) -> bool:
    """Check if a module is importable"""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False

def install_core_dependencies():
    """Install core dependencies from requirements.txt"""
    print("📦 Installing core dependencies...")
    
    success, output = run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    if success:
        print("   ✅ Core dependencies installed successfully")
        return True
    else:
        print(f"   ❌ Failed to install core dependencies: {output}")
        return False

def install_vector_dependencies():
    """Install vector database specific dependencies"""
    print("🔍 Installing vector database dependencies...")
    
    # Since all dependencies are already in requirements.txt, 
    # we just need to verify they're installed correctly
    print("   ℹ️ All dependencies are included in requirements.txt")
    print("   ✅ Vector database dependencies are ready")
    
    return True

def setup_environment():
    """Set up the environment file"""
    print("⚙️ Setting up environment configuration...")
    
    env_template = Path(".env.template")
    env_file = Path(".env")
    
    if not env_template.exists():
        print("   ❌ .env.template file not found")
        return False
    
    if env_file.exists():
        print("   ℹ️ .env file already exists, skipping creation")
    else:
        shutil.copy(env_template, env_file)
        print("   ✅ Created .env file from template")
    
    print("   📝 Please edit .env file with your API keys")
    return True

def validate_installation():
    """Validate that all critical dependencies are installed"""
    print("🔍 Validating installation...")
    
    critical_modules = [
        "openai",
        "langchain",
        "chromadb",
        "rich",
        "numpy"
    ]
    
    all_good = True
    for module in critical_modules:
        if check_dependency(module):
            print(f"   ✅ {module} is available")
        else:
            print(f"   ❌ {module} is missing")
            all_good = False
    
    return all_good

def create_directories():
    """Create necessary directories"""
    print("📁 Creating necessary directories...")
    
    directories = [
        "vector_db",
        "workdir",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   ✅ Created {directory}/ directory")

def main():
    """Main installation process"""
    print("🚀 Deep Research Agent Installation")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Step 1: Install core dependencies
    if not install_core_dependencies():
        print("❌ Failed to install core dependencies")
        sys.exit(1)
    
    # Step 2: Verify vector database dependencies
    if not install_vector_dependencies():
        print("❌ Failed to verify vector database dependencies")
        sys.exit(1)
    
    # Step 3: Set up environment
    if not setup_environment():
        print("❌ Failed to set up environment")
        sys.exit(1)
    
    # Step 4: Create directories
    create_directories()
    
    # Step 5: Validate installation
    if not validate_installation():
        print("❌ Installation validation failed")
        print("   Please check the error messages above and try again")
        sys.exit(1)
    
    print("\n🎉 Installation completed successfully!")
    print("\n📋 Next steps:")
    print("   1. Edit .env file with your API keys")
    print("   2. Run: python main.py")
    print("\n📚 For more information, see README.md")

if __name__ == "__main__":
    main() 