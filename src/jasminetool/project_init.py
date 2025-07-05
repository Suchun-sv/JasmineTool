#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project Initialization Module

This module handles project-specific initialization tasks.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from .utils import ConfigManager


class ProjectInitializer:
    """Handle project-specific initialization tasks"""
    
    def __init__(self, config: Dict[str, Any], target: str):
        """Initialize with configuration and target"""
        self.config = config
        self.target = target
        self.target_config = config.get(target, {})
        
        # Extract configuration values
        self.github_url = self.target_config.get('github_url', '')
        self.work_dir = Path(self.target_config.get('work_dir', ''))
        self.ssh_host = self.target_config.get('ssh_host', '')
        self.dvc_cache = self.target_config.get('dvc_cache', '')
        self.dvc_remote = self.target_config.get('dvc_remote', '')
        self.command_runner = self.target_config.get('command_runner', 'uv run')
    
    def check_and_install_tool(self, tool_name: str, check_cmd: str, install_cmd: str, description: str) -> bool:
        """Check if tool is installed and install if not"""
        try:
            # Check if tool is installed
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ {tool_name} is already installed")
                return True
            else:
                print(f"⚠ {tool_name} not found, installing...")
                
                # Install the tool
                install_result = subprocess.run(install_cmd, shell=True, text=True)
                
                if install_result.returncode == 0:
                    print(f"✓ {tool_name} installed successfully")
                    return True
                else:
                    print(f"✗ Failed to install {tool_name}")
                    return False
                    
        except Exception as e:
            print(f"✗ Error checking/installing {tool_name}: {e}")
            return False
    
    def clone_repository(self) -> bool:
        """Clone repository if work_dir doesn't exist"""
        if not self.github_url:
            print("⚠ No github_url specified in configuration")
            return False
        
        if self.work_dir.exists():
            print(f"✓ Work directory already exists: {self.work_dir}")
            return True
        
        try:
            print(f"📥 Cloning repository from {self.github_url}")
            print(f"📁 Target directory: {self.work_dir}")
            
            # Create parent directory if it doesn't exist
            self.work_dir.parent.mkdir(parents=True, exist_ok=True)
            
            # Clone repository
            clone_cmd = f"git clone {self.github_url} {self.work_dir}"
            result = subprocess.run(clone_cmd, shell=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ Repository cloned successfully")
                return True
            else:
                print(f"✗ Failed to clone repository")
                return False
                
        except Exception as e:
            print(f"✗ Error cloning repository: {e}")
            return False
    
    def setup_environment(self) -> bool:
        """Setup Python environment using uv"""
        try:
            if not self.work_dir.exists():
                print(f"✗ Work directory doesn't exist: {self.work_dir}")
                return False
            
            print(f"🔧 Setting up Python environment in {self.work_dir}")
            
            # Change to work directory
            original_cwd = os.getcwd()
            os.chdir(self.work_dir)
            
            try:
                # Check if init.sh exists
                init_script = self.work_dir / "init.sh"
                if init_script.exists():
                    print("📜 Found init.sh, running custom initialization script...")
                    result = subprocess.run("bash init.sh", shell=True, text=True)
                    
                    if result.returncode == 0:
                        print("✓ Custom initialization script completed successfully")
                        return True
                    else:
                        print("✗ Custom initialization script failed")
                        return False
                else:
                    print("🐍 Running default Python environment setup...")
                    
                    # Create virtual environment
                    print("Creating virtual environment...")
                    venv_result = subprocess.run("uv venv", shell=True, text=True)
                    
                    if venv_result.returncode != 0:
                        print("✗ Failed to create virtual environment")
                        return False
                    
                    # Sync dependencies
                    print("Syncing dependencies...")
                    sync_result = subprocess.run("uv sync", shell=True, text=True)
                    
                    if sync_result.returncode != 0:
                        print("✗ Failed to sync dependencies")
                        return False
                    
                    print("✓ Python environment setup completed successfully")
                    return True
                    
            finally:
                # Restore original working directory
                os.chdir(original_cwd)
                
        except Exception as e:
            print(f"✗ Error setting up environment: {e}")
            return False
    
    def ask_for_update(self) -> bool:
        """Ask user if they want to run update command"""
        try:
            response = input("\n🔄 Do you want to run update command? (y/n): ").lower().strip()
            return response in ['y', 'yes']
        except:
            return False
    
    def run_project_init(self, verbose: bool = False) -> bool:
        """Run the complete project initialization process"""
        print(f"🚀 Initializing project for target: {self.target}")
        print("=" * 60)
        
        if verbose:
            print(f"Configuration:")
            print(f"  GitHub URL: {self.github_url}")
            print(f"  Work Directory: {self.work_dir}")
            print(f"  SSH Host: {self.ssh_host}")
            print(f"  DVC Cache: {self.dvc_cache}")
            print(f"  DVC Remote: {self.dvc_remote}")
            print(f"  Command Runner: {self.command_runner}")
            print()
        
        success = True
        
        # Step 1: Check and install x-cmd
        if not self.check_and_install_tool(
            tool_name="x-cmd",
            check_cmd="which x",
            install_cmd='eval "$(curl https://get.x-cmd.com)"',
            description="x-cmd toolkit"
        ):
            success = False
        
        # Step 2: Check and install uv
        if not self.check_and_install_tool(
            tool_name="uv",
            check_cmd="which uv",
            install_cmd="curl -LsSf https://astral.sh/uv/install.sh | sh",
            description="uv Python package manager"
        ):
            success = False
        
        # Step 3: Clone repository if needed
        if not self.clone_repository():
            success = False
        
        # Step 4: Setup environment
        if not self.setup_environment():
            success = False
        
        # Step 5: Ask for update
        if success and self.ask_for_update():
            print("ℹ️  Update command will be implemented in future versions")
        
        print("=" * 60)
        if success:
            print("🎉 Project initialization completed successfully!")
            print(f"📁 Project location: {self.work_dir}")
            print("\nNext steps:")
            print("1. Navigate to the project directory")
            print("2. Activate the virtual environment")
            print("3. Start development")
        else:
            print("❌ Project initialization failed!")
            print("Please check the errors above and try again")
        
        return success


def init_project(config_path: str, target: str, verbose: bool = False) -> bool:
    """Initialize a project for the given target"""
    try:
        # Load configuration
        config = ConfigManager.load_config(config_path)
        
        # Check if target exists
        if target not in config:
            print(f"✗ Target '{target}' not found in configuration")
            return False
        
        # Initialize project
        initializer = ProjectInitializer(config, target)
        return initializer.run_project_init(verbose=verbose)
        
    except Exception as e:
        print(f"✗ Error initializing project: {e}")
        return False 