#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Initialization module for JasmineTool

This module handles the initialization of JasmineTool configuration.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from .utils import ConfigManager


class JasmineToolInitializer:
    """Initialize JasmineTool configuration and directory structure"""
    
    def __init__(self, base_dir: str = "."):
        """Initialize with base directory"""
        self.base_dir = Path(base_dir).resolve()
        self.jasmine_dir = self.base_dir / ".jasminetool"
        self.config_path = self.jasmine_dir / "config.yaml"
        self.logs_dir = self.jasmine_dir / "logs"
        self.temp_dir = self.jasmine_dir / "temp"
    
    def create_directory_structure(self) -> bool:
        """Create .jasminetool directory structure"""
        try:
            # Create main directory
            self.jasmine_dir.mkdir(exist_ok=True)
            print(f"✓ Created directory: {self.jasmine_dir}")
            
            # Create subdirectories
            self.logs_dir.mkdir(exist_ok=True)
            print(f"✓ Created logs directory: {self.logs_dir}")
            
            self.temp_dir.mkdir(exist_ok=True)
            print(f"✓ Created temp directory: {self.temp_dir}")
            
            return True
        except Exception as e:
            print(f"✗ Failed to create directory structure: {e}")
            return False
    
    def create_default_config(self) -> bool:
        """Create default configuration file"""
        try:
            if self.config_path.exists():
                print(f"⚠ Configuration file already exists: {self.config_path}")
                return True
            
            default_config = self._get_default_config()
            
            # Save configuration
            if ConfigManager.save_config(default_config, str(self.config_path)):
                print(f"✓ Created default configuration: {self.config_path}")
                return True
            else:
                print(f"✗ Failed to create configuration file")
                return False
        except Exception as e:
            print(f"✗ Failed to create default configuration: {e}")
            return False
    
    def create_gitignore(self) -> bool:
        """Create .gitignore file for .jasminetool directory"""
        try:
            gitignore_path = self.jasmine_dir / ".gitignore"
            
            gitignore_content = """# JasmineTool generated files
logs/
temp/
*.log
*.tmp
*.pid

# User-specific configurations
local_config.yaml
"""
            
            with open(gitignore_path, 'w', encoding='utf-8') as f:
                f.write(gitignore_content)
            
            print(f"✓ Created .gitignore file: {gitignore_path}")
            return True
        except Exception as e:
            print(f"✗ Failed to create .gitignore file: {e}")
            return False
    
    def copy_example_files(self) -> bool:
        """Copy example configuration files if they exist"""
        try:
            # Look for example files in the package
            examples_dir = Path(__file__).parent.parent.parent / "examples"
            
            if examples_dir.exists() and examples_dir.is_dir():
                target_examples_dir = self.jasmine_dir / "examples"
                target_examples_dir.mkdir(exist_ok=True)
                
                # Copy example files
                for example_file in examples_dir.glob("*.yaml"):
                    target_file = target_examples_dir / example_file.name
                    shutil.copy2(example_file, target_file)
                    print(f"✓ Copied example file: {example_file.name}")
                
                return True
            else:
                print("ⓘ No example files found to copy")
                return True
        except Exception as e:
            print(f"✗ Failed to copy example files: {e}")
            return False
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "# JasmineTool Configuration": None,
            "# This is the default configuration created by 'jasminetool init'": None,
            "# Modify this file to suit your needs": None,
            
            # Global settings
            "sweep_file": "./.jasminetool/sweep_config.yaml",
            "pattern": "wandb agent",
            "src_dir": str(self.base_dir),  # Record current directory as source directory
            
            # Local GPU execution
            "local_gpu": {
                "mode": "local",
                "gpu_config": "0",
                "num_processes": 1,
            },
            
            # Remote execution example
            "remote_server": {
                "mode": "remote",
                "ssh_host": "user@remote-server.com",
                "work_dir": "/path/to/project",
                "gpu_config": "0",
                "num_processes": 1,
                "sync_method": "git",
                "git_operations": [
                    "git fetch origin",
                    "git checkout {branch}",
                    "git pull origin {branch}",
                ]
            },
            
            # SLURM execution example
            "slurm_cluster": {
                "mode": "slurm",
                "gpu_config": "0",
                "num_processes": 1,
                "slurm_config": {
                    "job-name": "jasmine-sweep",
                    "time": "24:00:00",
                    "nodes": 1,
                    "ntasks-per-node": 1,
                    "gres": "gpu:1",
                    "partition": "gpu",
                }
            },
            
            # Pre-commands (optional)
            "pre_commands": [
                {
                    "command": "echo 'Starting JasmineTool execution'",
                    "working_dir": "."
                }
            ]
        }
    
    def initialize(self, force: bool = False, verbose: bool = False) -> bool:
        """Initialize JasmineTool configuration"""
        print("Initializing JasmineTool...")
        print("=" * 50)
        
        if verbose:
            print(f"Base directory: {self.base_dir}")
            print(f"JasmineTool directory: {self.jasmine_dir}")
        
        # Check if already initialized
        if self.jasmine_dir.exists() and not force:
            print(f"⚠ JasmineTool already initialized in {self.jasmine_dir}")
            print("  Use --force to reinitialize")
            return True
        
        success = True
        
        # Create directory structure
        if not self.create_directory_structure():
            success = False
        
        # Create default configuration
        if not self.create_default_config():
            success = False
        
        # Create .gitignore
        if not self.create_gitignore():
            success = False
        
        # Copy example files
        if not self.copy_example_files():
            success = False
        
        print("=" * 50)
        if success:
            print("🎉 JasmineTool initialized successfully!")
            print(f"📁 Configuration directory: {self.jasmine_dir}")
            print(f"⚙️  Configuration file: {self.config_path}")
            print("\nNext steps:")
            print("1. Edit the configuration file to match your setup")
            print("2. Run 'jasminetool <target>' to execute tasks")
            print("3. Use 'jasminetool --help' for more information")
        else:
            print("❌ JasmineTool initialization failed!")
        
        return success


def init_jasminetool(base_dir: str = ".", force: bool = False, verbose: bool = False) -> bool:
    """Initialize JasmineTool in the specified directory"""
    initializer = JasmineToolInitializer(base_dir)
    return initializer.initialize(force=force, verbose=verbose) 