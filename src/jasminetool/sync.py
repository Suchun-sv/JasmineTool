#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Synchronization Module

This module handles git and DVC synchronization operations.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from .utils import ConfigManager, GitManager
from .ssh_executor import RemoteTargetExecutor


class SyncManager:
    """Handle synchronization operations between local and remote repositories"""
    
    def __init__(self, config: Dict[str, Any], target: str):
        """Initialize with configuration and target"""
        self.config = config
        self.target = target
        self.target_config = config.get(target, {})
        
        # Extract configuration values
        self.github_url = self.target_config.get('github_url', '')
        self.work_dir = Path(self.target_config.get('work_dir', ''))
        self.dvc_cache = self.target_config.get('dvc_cache', '')
        self.dvc_remote = self.target_config.get('dvc_remote', '')
        
        # Command runner for executing commands in virtual environment
        self.command_runner = self.target_config.get('command_runner', 'uv run')
        
        # Source directory info from global config
        self.src_dir = Path(self.config.get('src_dir', Path.cwd()))
        self.current_branch = ""
    
    def get_git_remote_url(self, directory: Path) -> Optional[str]:
        """Get the remote URL of a git repository"""
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=directory,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return None
        except Exception as e:
            print(f"✗ Error getting git remote URL: {e}")
            return None
    
    def normalize_git_url(self, url: str) -> str:
        """Normalize git URL for comparison"""
        if not url:
            return ""
        
        # Remove .git suffix if present
        if url.endswith('.git'):
            url = url[:-4]
        
        # Convert SSH format to HTTPS format for comparison
        if url.startswith('git@'):
            # Convert git@github.com:user/repo to https://github.com/user/repo
            url = url.replace('git@', 'https://')
            url = url.replace(':', '/')
        
        return url.lower()
    
    def check_git_urls_match(self) -> bool:
        """Check if source directory github_url matches target github_url"""
        if not self.github_url:
            print("✗ No github_url specified in target configuration")
            return False
        
        # Get source directory's git remote URL from config
        src_git_url = self.get_git_remote_url(self.src_dir)
        if not src_git_url:
            print(f"✗ Source directory {self.src_dir} is not a git repository or has no remote")
            return False
        
        # Normalize URLs for comparison
        src_normalized = self.normalize_git_url(src_git_url)
        target_normalized = self.normalize_git_url(self.github_url)
        
        print(f"📍 Source directory: {self.src_dir}")
        print(f"📍 Source git URL: {src_git_url}")
        print(f"📍 Target git URL: {self.github_url}")
        
        if src_normalized == target_normalized:
            print("✓ Git URLs match")
            return True
        else:
            print("✗ Git URLs do not match")
            print(f"  Source (normalized): {src_normalized}")
            print(f"  Target (normalized): {target_normalized}")
            return False
    
    def check_git_clean(self, directory: Path) -> bool:
        """Check if git repository is clean"""
        try:
            # Check git status
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=directory,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"✗ Git status check failed in {directory}")
                return False
            
            if result.stdout.strip():
                print(f"✗ Git repository is not clean in {directory}")
                print("  Uncommitted changes found:")
                for line in result.stdout.strip().split('\n'):
                    print(f"    {line}")
                return False
            else:
                print(f"✓ Git repository is clean in {directory}")
                return True
                
        except Exception as e:
            print(f"✗ Error checking git status: {e}")
            return False
    
    def check_dvc_clean(self, directory: Path) -> bool:
        """Check if DVC repository is clean"""
        try:
            # Check if DVC is initialized
            dvc_dir = directory / '.dvc'
            if not dvc_dir.exists():
                print(f"ℹ️  DVC not initialized in {directory}, skipping DVC check")
                return True
            
            # Check DVC status using uv run
            cmd = f"{self.command_runner} dvc status".split()
            result = subprocess.run(
                cmd,
                cwd=directory,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"✗ DVC status check failed in {directory}")
                return False
            
            if result.stdout.strip() != "Data and pipelines are up to date.":
                print(f"✗ DVC repository is not clean in {directory}")
                print("  DVC changes found:")
                for line in result.stdout.strip().split('\n'):
                    print(f"    {line}")
                return False
            else:
                print(f"✓ DVC repository is clean in {directory}")
                return True
                
        except Exception as e:
            print(f"✗ Error checking DVC status: {e}")
            return False
    
    def get_current_branch(self, directory: Path) -> str:
        """Get current git branch"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=directory,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                branch = result.stdout.strip()
                print(f"📍 Current branch: {branch}")
                return branch
            else:
                print("✗ Failed to get current branch")
                return "main"
                
        except Exception as e:
            print(f"✗ Error getting current branch: {e}")
            return "main"
    
    def setup_dvc_cache(self) -> bool:
        """Setup DVC cache directory"""
        if not self.dvc_cache:
            print("ℹ️  No DVC cache directory specified, skipping")
            return True
        
        try:
            print(f"🔧 Setting up DVC cache: {self.dvc_cache}")
            
            # Set DVC cache directory using uv run
            cmd = f"{self.command_runner} dvc cache dir --local {self.dvc_cache}".split()
            result = subprocess.run(
                cmd,
                cwd=self.work_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"✓ DVC cache directory set to: {self.dvc_cache}")
                return True
            else:
                print(f"✗ Failed to set DVC cache directory")
                print(f"  Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"✗ Error setting up DVC cache: {e}")
            return False
    
    def setup_dvc_remote(self) -> bool:
        """Setup DVC remote"""
        if not self.dvc_remote:
            print("ℹ️  No DVC remote specified, skipping")
            return True
        
        try:
            print(f"🔧 Setting up DVC remote: {self.dvc_remote}")
            
            # Add DVC remote using uv run
            cmd = f"{self.command_runner} dvc remote add --local jasmine_remote {self.dvc_remote} --force".split()
            result = subprocess.run(
                cmd,
                cwd=self.work_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"✓ DVC remote 'jasmine_remote' added: {self.dvc_remote}")
                return True
            else:
                # Check if remote already exists
                if "remote 'jasmine_remote' already exists" in result.stderr:
                    print(f"ℹ️  DVC remote 'jasmine_remote' already exists")
                    return True
                else:
                    print(f"✗ Failed to add DVC remote")
                    print(f"  Error: {result.stderr}")
                    return False
                
        except Exception as e:
            print(f"✗ Error setting up DVC remote: {e}")
            return False
    
    def dvc_pull(self) -> bool:
        """Pull data from DVC remote"""
        if not self.dvc_remote:
            print("ℹ️  No DVC remote specified, skipping DVC pull")
            return True
        
        try:
            print(f"📥 Pulling data from DVC remote...")
            
            # Pull data from remote using uv run
            cmd = f"{self.command_runner} dvc pull -r jasmine_remote".split()
            result = subprocess.run(
                cmd,
                cwd=self.work_dir,
                text=True
            )
            
            if result.returncode == 0:
                print(f"✓ DVC pull completed successfully")
                return True
            else:
                print(f"✗ DVC pull failed")
                return False
                
        except Exception as e:
            print(f"✗ Error during DVC pull: {e}")
            return False
    
    def sync_git_branch(self) -> bool:
        """Sync Git branch in work directory with source directory"""
        try:
            print(f"🔄 Syncing Git branch to: {self.current_branch}")
            
            # Check if work directory has .git
            git_dir = self.work_dir / ".git"
            if not git_dir.exists():
                print("✗ Work directory is not a Git repository")
                return False
            
            # Fetch all branches
            print("📥 Fetching latest changes from remote...")
            fetch_result = subprocess.run(
                ['git', 'fetch', '--all'],
                cwd=self.work_dir,
                capture_output=True,
                text=True
            )
            
            if fetch_result.returncode != 0:
                print(f"✗ Failed to fetch: {fetch_result.stderr}")
                return False
            
            # Check if branch exists locally
            branch_check = subprocess.run(
                ['git', 'branch', '--list', self.current_branch],
                cwd=self.work_dir,
                capture_output=True,
                text=True
            )
            
            if branch_check.stdout.strip():
                # Branch exists locally, checkout and reset hard
                print(f"🔄 Checking out existing branch: {self.current_branch}")
                checkout_result = subprocess.run(
                    ['git', 'checkout', self.current_branch],
                    cwd=self.work_dir,
                    capture_output=True,
                    text=True
                )
                
                if checkout_result.returncode != 0:
                    print(f"✗ Failed to checkout branch: {checkout_result.stderr}")
                    return False
                
                # Hard reset to origin branch (force overwrite)
                print(f"🔄 Force pulling changes from origin/{self.current_branch}")
                reset_result = subprocess.run(
                    ['git', 'reset', '--hard', f'origin/{self.current_branch}'],
                    cwd=self.work_dir,
                    capture_output=True,
                    text=True
                )
                
                if reset_result.returncode != 0:
                    print(f"✗ Failed to reset to origin: {reset_result.stderr}")
                    return False
            else:
                # Branch doesn't exist locally, checkout from remote
                print(f"🔄 Checking out new branch from remote: {self.current_branch}")
                checkout_result = subprocess.run(
                    ['git', 'checkout', '-b', self.current_branch, f'origin/{self.current_branch}'],
                    cwd=self.work_dir,
                    capture_output=True,
                    text=True
                )
                
                if checkout_result.returncode != 0:
                    print(f"✗ Failed to checkout new branch: {checkout_result.stderr}")
                    return False
            
            # Verify we're on the correct branch
            current_branch_result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=self.work_dir,
                capture_output=True,
                text=True
            )
            
            if current_branch_result.returncode == 0:
                actual_branch = current_branch_result.stdout.strip()
                if actual_branch == self.current_branch:
                    print(f"✓ Successfully synced to branch: {self.current_branch}")
                    return True
                else:
                    print(f"✗ Branch mismatch: expected {self.current_branch}, got {actual_branch}")
                    return False
            else:
                print(f"✗ Failed to verify current branch")
                return False
                
        except Exception as e:
            print(f"✗ Error syncing Git branch: {e}")
            return False
    
    def run_sync(self, verbose: bool = False) -> bool:
        """Run the complete synchronization process"""
        print(f"🔄 Starting synchronization for target: {self.target}")
        print("=" * 60)
        
        if verbose:
            print(f"Configuration:")
            print(f"  Source directory: {self.src_dir}")
            print(f"  Target work directory: {self.work_dir}")
            print(f"  GitHub URL: {self.github_url}")
            print(f"  DVC Cache: {self.dvc_cache}")
            print(f"  DVC Remote: {self.dvc_remote}")
            print(f"  Command runner: {self.command_runner}")
            print()
        
        # Step 1: Check if git URLs match
        if not self.check_git_urls_match():
            print("💔 Git URLs do not match, aborting sync")
            return False
        
        # Step 2: Check if source directory is clean
        if not self.check_git_clean(self.src_dir):
            print("💔 Source directory is not clean, aborting sync")
            return False
        
        if not self.check_dvc_clean(self.src_dir):
            print("💔 Source DVC is not clean, aborting sync")
            return False
        
        # Step 3: Get current branch
        self.current_branch = self.get_current_branch(self.src_dir)
        
        # Step 4: Check if work directory exists
        if not self.work_dir.exists():
            print(f"✗ Work directory does not exist: {self.work_dir}")
            print(f"  Please run 'jasminetool -t {self.target} init' first")
            return False
        
        # Step 5: Change to work directory and sync Git
        print(f"📁 Changing to work directory: {self.work_dir}")
        
        # Sync Git branch and pull changes
        if not self.sync_git_branch():
            print("💔 Failed to sync Git branch")
            return False
        
        # Setup DVC cache
        if not self.setup_dvc_cache():
            print("💔 Failed to setup DVC cache")
            return False
        
        # Setup DVC remote
        if not self.setup_dvc_remote():
            print("💔 Failed to setup DVC remote")
            return False
        
        # Pull data from DVC remote
        if not self.dvc_pull():
            print("💔 Failed to pull data from DVC remote")
            return False
        
        print("=" * 60)
        print("🎉 Synchronization completed successfully!")
        print(f"📍 Current branch: {self.current_branch}")
        print(f"📁 Work directory: {self.work_dir}")
        
        return True


def sync_project(config_path: str, target: str, verbose: bool = False) -> bool:
    """Synchronize a project for the given target"""
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
                print(f"🌐 Executing sync command on remote host: {ssh_host}")
            
            return sync_project_remote(config_path, config, target, target_config, verbose)
        else:
            # Local execution
            if verbose:
                print("🏠 Executing sync command locally")
            
            # Run synchronization locally
            sync_manager = SyncManager(config, target)
            return sync_manager.run_sync(verbose=verbose)
        
    except Exception as e:
        print(f"✗ Error during synchronization: {e}")
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


def sync_git_branch_remote(remote_executor: RemoteTargetExecutor, work_dir: str, current_branch: str, verbose: bool = False) -> bool:
    """Sync git branch on remote host"""
    print(f"🔄 Syncing git branch: {current_branch}")
    
    # Fetch all branches
    print("📥 Fetching latest changes from remote...")
    result = remote_executor.ssh.execute_command("git fetch --all", stream_output=True)
    if result.returncode != 0:
        print(f"✗ Failed to fetch from remote")
        return False
    
    # Checkout and sync the branch
    print(f"🔄 Checking out branch: {current_branch}")
    result = remote_executor.ssh.execute_command(f"git checkout {current_branch}", stream_output=True)
    if result.returncode != 0:
        print(f"✗ Failed to checkout branch: {current_branch}")
        return False
    
    print(f"🔄 Pulling latest changes...")
    result = remote_executor.ssh.execute_command(f"git reset --hard origin/{current_branch}", stream_output=True)
    if result.returncode != 0:
        print(f"✗ Failed to reset to origin/{current_branch}")
        return False
    
    print("✅ Git branch synced successfully")
    return True


def setup_dvc_cache_remote(remote_executor: RemoteTargetExecutor, work_dir: str, dvc_cache: str, command_runner: str, verbose: bool = False) -> bool:
    """Setup DVC cache on remote host"""
    if not dvc_cache:
        print("ℹ️  No DVC cache directory specified, skipping")
        return True
    
    print(f"🔧 Setting up DVC cache: {dvc_cache}")
    
    # Get the correct uv command
    uv_cmd = get_uv_command(remote_executor)
    
    # Replace uv in command_runner if needed
    if command_runner.startswith("uv run"):
        command_runner = command_runner.replace("uv run", f"{uv_cmd} run")
    
    result = remote_executor.ssh.execute_command(f'{command_runner} dvc cache dir --local "{dvc_cache}"', stream_output=True)
    
    if result.returncode == 0:
        print("✅ DVC cache directory set successfully")
        return True
    else:
        print(f"✗ Failed to set DVC cache directory")
        return False


def setup_dvc_remote_remote(remote_executor: RemoteTargetExecutor, work_dir: str, dvc_remote: str, command_runner: str, verbose: bool = False) -> bool:
    """Setup DVC remote on remote host"""
    if not dvc_remote:
        print("ℹ️  No DVC remote specified, skipping")
        return True
    
    print(f"🔧 Setting up DVC remote: {dvc_remote}")
    
    # Get the correct uv command
    uv_cmd = get_uv_command(remote_executor)
    
    # Replace uv in command_runner if needed
    if command_runner.startswith("uv run"):
        command_runner = command_runner.replace("uv run", f"{uv_cmd} run")
    
    result = remote_executor.ssh.execute_command(f'{command_runner} dvc remote add --local jasmine_remote "{dvc_remote}"', stream_output=True)
    
    if result.returncode == 0:
        print("✅ DVC remote 'jasmine_remote' added successfully")
        return True
    else:
        # Check if remote already exists
        if "remote 'jasmine_remote' already exists" in result.stderr:
            print("ℹ️  DVC remote 'jasmine_remote' already exists")
            return True
        else:
            print(f"✗ Failed to add DVC remote")
            return False


def dvc_pull_remote(remote_executor: RemoteTargetExecutor, work_dir: str, dvc_remote: str, command_runner: str, verbose: bool = False) -> bool:
    """Pull DVC data on remote host"""
    if not dvc_remote:
        print("ℹ️  No DVC remote specified, skipping DVC pull")
        return True
    
    print("📥 Pulling DVC data...")
    
    # Get the correct uv command
    uv_cmd = get_uv_command(remote_executor)
    
    # Replace uv in command_runner if needed
    if command_runner.startswith("uv run"):
        command_runner = command_runner.replace("uv run", f"{uv_cmd} run")
    
    result = remote_executor.ssh.execute_command(f'{command_runner} dvc pull -r jasmine_remote', stream_output=True)
    
    if result.returncode == 0:
        print("✅ DVC data pulled successfully")
        return True
    else:
        print(f"✗ Failed to pull DVC data")
        return False


def get_current_branch_local(config: Dict[str, Any], target: str) -> str:
    """Get current branch from local repository"""
    try:
        # Create a temporary SyncManager to get source directory
        sync_manager = SyncManager(config, target)
        
        # Get current branch from local repository
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=sync_manager.src_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            branch = result.stdout.strip()
            print(f"📍 Current local branch: {branch}")
            return branch
        else:
            print("✗ Failed to get current branch, using main")
            return "main"
            
    except Exception as e:
        print(f"✗ Error getting current branch: {e}, using main")
        return "main"


def sync_project_remote(config_path: str, config: Dict[str, Any], target: str, target_config: Dict[str, Any], verbose: bool = False) -> bool:
    """Sync project on remote host"""
    try:
        # Create remote executor
        remote_executor = RemoteTargetExecutor(target_config, verbose)
        
        # Validate connection
        if not remote_executor.validate_connection():
            return False
        
        # First, perform local validation
        if not perform_local_validation(config_path, config, target, target_config, verbose):
            return False
        
        # Get current branch from local repository
        current_branch = get_current_branch_local(config, target)
        
        # Get configuration
        work_dir = target_config.get('work_dir', '')
        dvc_cache = target_config.get('dvc_cache', '')
        dvc_remote = target_config.get('dvc_remote', '')
        command_runner = target_config.get('command_runner', 'uv run')
        
        print(f"🔄 Starting remote synchronization...")
        print(f"📁 Work directory: {work_dir}")
        print(f"🌿 Branch: {current_branch}")
        if dvc_cache:
            print(f"💾 DVC cache: {dvc_cache}")
        if dvc_remote:
            print(f"☁️  DVC remote: {dvc_remote}")
        print(f"▶️  Command runner: {command_runner}")
        print("=" * 60)
        
        # Step 1: Sync git branch
        if not sync_git_branch_remote(remote_executor, work_dir, current_branch, verbose):
            return False
        
        # Step 2: Setup DVC cache
        if not setup_dvc_cache_remote(remote_executor, work_dir, dvc_cache, command_runner, verbose):
            return False
        
        # Step 3: Setup DVC remote
        if not setup_dvc_remote_remote(remote_executor, work_dir, dvc_remote, command_runner, verbose):
            return False
        
        # Step 4: Pull DVC data
        if not dvc_pull_remote(remote_executor, work_dir, dvc_remote, command_runner, verbose):
            return False
        
        print("=" * 60)
        print("🎉 Project synchronization completed successfully!")
        print(f"📁 Project location: {work_dir}")
        print(f"🌿 Branch: {current_branch}")
        print("✅ Git branch synced")
        print("✅ DVC data synchronized")
        
        return True
        
    except Exception as e:
        print(f"❌ Error syncing project remotely: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def perform_local_validation(config_path: str, config: Dict[str, Any], target: str, target_config: Dict[str, Any], verbose: bool = False) -> bool:
    """Perform local validation checks before remote sync"""
    try:
        # Create a temporary SyncManager instance just for validation
        sync_manager = SyncManager(config, target)
        
        # Perform the same validation checks as local sync
        if not sync_manager.check_git_urls_match():
            print("❌ Git URLs do not match")
            return False
        
        if not sync_manager.check_git_clean(sync_manager.src_dir):
            print("❌ Source directory is not clean")
            return False
        
        if not sync_manager.check_dvc_clean(sync_manager.src_dir):
            print("❌ Source DVC is not clean")
            return False
        
        print("✅ Local validation passed")
        return True
        
    except Exception as e:
        print(f"❌ Error in local validation: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


 