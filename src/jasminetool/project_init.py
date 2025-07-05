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
from typing import Dict, Any, Optional, List

from .utils import ConfigManager
from .ssh_executor import RemoteTargetExecutor


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
        # if success and self.ask_for_update():
        #     print("ℹ️  Update command will be implemented in future versions")
        
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
        
        target_config = config[target]
        
        # Check if this is a remote target (has ssh_host)
        ssh_host = target_config.get('ssh_host')
        
        if ssh_host:
            # Remote execution
            if verbose:
                print(f"🌐 Executing init command on remote host: {ssh_host}")
            
            return init_project_remote(config, target, target_config, verbose)
        else:
            # Local execution
            if verbose:
                print("🏠 Executing init command locally")
            
            # Initialize project locally
            initializer = ProjectInitializer(config, target)
            return initializer.run_project_init(verbose=verbose)
        
    except Exception as e:
        print(f"✗ Error initializing project: {e}")
        return False


def init_project_remote(config: Dict[str, Any], target: str, target_config: Dict[str, Any], verbose: bool = False) -> bool:
    """Initialize a project on remote host"""
    try:
        # Create remote executor
        remote_executor = RemoteTargetExecutor(target_config, verbose)
        
        # Validate connection
        if not remote_executor.validate_connection():
            return False
        
        # Get configuration values
        github_url = target_config.get('github_url', '')
        work_dir = target_config.get('work_dir', '')
        
        print(f"🚀 Initializing project for remote target: {target}")
        print("=" * 60)
        
        if verbose:
            print(f"📁 Work directory: {work_dir}")
            print(f"📥 GitHub URL: {github_url}")
            print()
        
        # Step 1: Check and install x-cmd
        if not check_and_install_x_cmd_remote(remote_executor, verbose):
            return False
        
        # Step 2: Check and install uv
        if not check_and_install_uv_remote(remote_executor, verbose):
            return False
        
        # Step 3: Clone repository if needed
        if github_url:
            if not clone_repository_remote(remote_executor, github_url, work_dir, verbose):
                return False
        
        # Step 4: Setup Python environment
        if not setup_environment_remote(remote_executor, work_dir, verbose):
            return False
        
        # Step 5: Ask for update
        if ask_for_update():
            print("ℹ️  Update command will be implemented in future versions")
        
        print("=" * 60)
        print("🎉 Project initialization completed successfully!")
        print(f"📁 Project location: {work_dir}")
        print("\nNext steps:")
        print("1. Navigate to the project directory")
        print("2. Activate the virtual environment")
        print("3. Start development")
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing project remotely: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def check_and_install_x_cmd_remote(remote_executor: RemoteTargetExecutor, verbose: bool = False) -> bool:
    """Check and install x-cmd on remote host"""
    print("🔧 Checking x-cmd installation...")
    
    # Check if x-cmd is installed
    result = remote_executor.ssh.execute_command("command -v x", no_work_dir=True)
    
    if result.returncode == 0:
        print("✓ x-cmd is already installed")
        return True
    else:
        print("⚠️ x-cmd not found, installing...")
        
        # Install x-cmd (with real-time output streaming)
        result = remote_executor.ssh.execute_command(
            'eval "$(curl https://get.x-cmd.com)"', 
            no_work_dir=True,
            stream_output=True,
            force_pty=True
        )
        
        if result.returncode == 0:
            print("✓ x-cmd installed successfully")
            return True
        else:
            print("✗ Failed to install x-cmd")
            print("   Please check the remote host network connection and try again")
            return False


def check_and_install_uv_remote(remote_executor: RemoteTargetExecutor, verbose: bool = False) -> bool:
    """Check and install uv on remote host"""
    print("🔧 Checking uv installation...")
    
    # Check if uv is installed
    result = remote_executor.ssh.execute_command("command -v uv", no_work_dir=True)
    
    if result.returncode == 0:
        print("✓ uv is already installed")
        return True
    else:
        print("⚠️ uv not found, installing...")
        
        # Install uv (with real-time output streaming)
        result = remote_executor.ssh.execute_command(
            "curl -LsSf https://astral.sh/uv/install.sh | sh",
            no_work_dir=True,
            stream_output=True,
            force_pty=True
        )
        
        if result.returncode == 0:
            print("✓ uv installed successfully")
            # Source bashrc to update PATH (Note: this may not affect current session)
            remote_executor.ssh.execute_command("source ~/.bashrc", no_work_dir=True)
            return True
        else:
            print("✗ Failed to install uv")
            print("   Please check the remote host network connection and try again")
            return False


def clone_repository_remote(remote_executor: RemoteTargetExecutor, github_url: str, work_dir: str, verbose: bool = False) -> bool:
    """Clone repository on remote host"""
    print("📥 Checking repository...")
    
    # Check if work directory exists
    result = remote_executor.ssh.execute_command(f"test -d {work_dir}", no_work_dir=True)
    
    if result.returncode == 0:
        print(f"✓ Work directory already exists: {work_dir}")
        
        # Check if it's a git repository
        print("📋 Checking if it is a git repository...")
        result = remote_executor.ssh.execute_command(f"test -d {work_dir}/.git", no_work_dir=True)
        
        if result.returncode == 0:
            print("✓ Directory is a git repository")
        else:
            print("⚠️  Directory exists but is not a git repository")
        
        return True
    else:
        print(f"📥 Cloning repository from {github_url}")
        print(f"📁 Target directory: {work_dir}")
        
        # Create parent directory if needed
        parent_dir = str(Path(work_dir).parent)
        result = remote_executor.ssh.execute_command(f"mkdir -p {parent_dir}", no_work_dir=True)
        
        if result.returncode != 0:
            print(f"✗ Failed to create parent directory: {parent_dir}")
            if result.stderr:
                print(f"   Error: {result.stderr}")
            return False
        
        # Clone repository (with real-time output streaming)
        result = remote_executor.ssh.execute_command(
            f'git clone "{github_url}" "{work_dir}"',
            no_work_dir=True,
            stream_output=True,
            force_pty=True
        )
        
        if result.returncode == 0:
            print("✓ Repository cloned successfully")
            return True
        else:
            print(f"✗ Failed to clone repository (exit code: {result.returncode})")
            if result.stdout and verbose:
                print(f"   Output: {result.stdout}")
            print("   Please check the GitHub URL and SSH/HTTPS access permissions")
            return False


def get_uv_command(remote_executor: RemoteTargetExecutor) -> str:
    """Get the correct uv command path"""
    # Try different possible uv locations
    possible_paths = [
        "uv",  # Already in PATH
        "~/.local/bin/uv",  # Standard user installation
        "~/.cargo/bin/uv",  # Cargo installation
        "$HOME/.local/bin/uv",  # Alternative home reference
    ]
    
    for uv_path in possible_paths:
        result = remote_executor.ssh.execute_command(f"command -v {uv_path}", no_work_dir=True)
        if result.returncode == 0:
            return uv_path
    
    # If nothing found, try with PATH update
    return "export PATH=\"$HOME/.local/bin:$HOME/.cargo/bin:$PATH\" && uv"


def setup_environment_remote(remote_executor: RemoteTargetExecutor, work_dir: str, verbose: bool = False) -> bool:
    """Setup Python environment on remote host"""
    print("🐍 Setting up Python environment...")
    
    # Get the correct uv command
    uv_cmd = get_uv_command(remote_executor)
    if verbose:
        print(f"Using uv command: {uv_cmd}")
    
    # Check if init.sh exists
    result = remote_executor.ssh.execute_command("test -f init.sh")
    
    if result.returncode == 0:
        print("📜 Found init.sh, running custom initialization script...")
        
        # Run init.sh with proper PATH setup and environment variables
        env_setup = "export PATH=\"$HOME/.local/bin:$HOME/.cargo/bin:$PATH\" TERM=xterm-256color FORCE_COLOR=1 &&"
        init_cmd = f"{env_setup} bash init.sh"
        result = remote_executor.ssh.execute_command(init_cmd, stream_output=True, force_pty=True)
        
        if result.returncode == 0:
            print("✓ Custom initialization script completed successfully")
            return True
        else:
            print(f"✗ Custom initialization script failed (exit code: {result.returncode})")
            if result.stdout and verbose:
                print(f"   Output: {result.stdout}")
            print("   Please check the init.sh script for errors")
            print("   Note: Make sure uv commands in init.sh use full path or update PATH")
            return False
    else:
        print("📜 No init.sh found, setting up standard environment...")
        
        # Standard setup commands
        setup_commands = [
            f"export PATH=\"$HOME/.local/bin:$HOME/.cargo/bin:$PATH\" TERM=xterm-256color FORCE_COLOR=1",
            f"{uv_cmd} venv --python=3.10",
            f"{uv_cmd} sync"
        ]
        
        for cmd in setup_commands:
            print(f"🔧 Running: {cmd}")
            result = remote_executor.ssh.execute_command(cmd, stream_output=True, force_pty=True)
            
            if result.returncode != 0:
                print(f"✗ Command failed: {cmd}")
                return False
        
        print("✓ Standard environment setup completed successfully")
        return True


def ask_for_update() -> bool:
    """Ask user if they want to run update command"""
    try:
        response = input("\n🔄 Do you want to run update command? (y/n): ").lower().strip()
        return response in ['y', 'yes']
    except:
        return False 