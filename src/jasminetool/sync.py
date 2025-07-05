#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Synchronization Module

This module handles git and DVC synchronization operations.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from .utils import ConfigManager, GitManager


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
            cmd = f"{self.command_runner} dvc remote add --local jasmine_remote {self.dvc_remote}".split()
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
        
        # Run synchronization
        sync_manager = SyncManager(config, target)
        return sync_manager.run_sync(verbose=verbose)
        
    except Exception as e:
        print(f"✗ Error during synchronization: {e}")
        return False 