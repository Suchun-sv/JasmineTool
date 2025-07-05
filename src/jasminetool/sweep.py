#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sweep Module

This module provides functionality to run wandb sweep commands and integrate with VS Code tasks.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from .utils import ConfigManager


class SweepManager:
    """Handle wandb sweep operations"""
    
    def __init__(self, config_path: str):
        """Initialize with configuration path"""
        self.config_path = Path(config_path)
        self.config: Optional[Dict[str, Any]] = None
        self.sweep_file = ""
    
    def load_config(self) -> bool:
        """Load configuration from file"""
        try:
            if not self.config_path.exists():
                print(f"✗ Sweep configuration file not found: {self.config_path}")
                return False
            
            # For sweep, we load the sweep config directly, not the main JasmineTool config
            if self.config_path.suffix.lower() in ['.yaml', '.yml']:
                import yaml
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
            else:
                print(f"✗ Unsupported config file format: {self.config_path}")
                return False
            
            return True
        except Exception as e:
            print(f"✗ Error loading sweep configuration: {e}")
            return False
    
    def get_sweep_log_file(self) -> str:
        """Get the sweep log file path"""
        if not self.sweep_file:
            # Try to get sweep_file from main JasmineTool config
            jasmine_config_path = Path(".jasminetool/config.yaml")
            if jasmine_config_path.exists():
                try:
                    jasmine_config = ConfigManager.load_config(str(jasmine_config_path))
                    self.sweep_file = jasmine_config.get('sweep_file', '.jasminetool/sweep.log')
                except:
                    self.sweep_file = '.jasminetool/sweep.log'
            else:
                self.sweep_file = '.jasminetool/sweep.log'
        
        return self.sweep_file
    
    def run_wandb_sweep(self, verbose: bool = False) -> bool:
        """Run wandb sweep command with config file"""
        try:
            if not self.load_config():
                return False
            
            print(f"🔥 Running wandb sweep with config: {self.config_path}")
            
            # Get sweep log file
            sweep_log_file = self.get_sweep_log_file()
            
            # Ensure log directory exists
            log_dir = Path(sweep_log_file).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Build the command
            cmd = f"wandb sweep {self.config_path} 2>&1 | tee {sweep_log_file}"
            
            if verbose:
                print(f"Command: {cmd}")
                print(f"Log file: {sweep_log_file}")
            
            print(f"📝 Output will be logged to: {sweep_log_file}")
            print("🚀 Starting wandb sweep...")
            
            # Execute the command
            result = subprocess.run(cmd, shell=True, text=True)
            
            if result.returncode == 0:
                print("✅ Wandb sweep completed successfully!")
                print(f"📄 Log saved to: {sweep_log_file}")
                return True
            else:
                print("❌ Wandb sweep failed!")
                print(f"📄 Check log file for details: {sweep_log_file}")
                return False
                
        except Exception as e:
            print(f"✗ Error running wandb sweep: {e}")
            return False


class VSCodeTasksManager:
    """Handle VS Code tasks.json integration"""
    
    def __init__(self):
        """Initialize VS Code tasks manager"""
        self.vscode_dir = Path(".vscode")
        self.tasks_file = self.vscode_dir / "tasks.json"
    
    def ensure_vscode_dir(self) -> bool:
        """Ensure .vscode directory exists"""
        try:
            self.vscode_dir.mkdir(exist_ok=True)
            return True
        except Exception as e:
            print(f"✗ Error creating .vscode directory: {e}")
            return False

    
    def save_tasks(self, tasks: Dict[str, Any]) -> bool:
        """Save tasks.json file"""
        try:
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"✗ Error saving tasks.json: {e}")
            return False
    
    def get_sweep_log_file_from_config(self) -> str:
        """Get sweep log file path from JasmineTool config"""
        try:
            jasmine_config_path = Path(".jasminetool/config.yaml")
            if jasmine_config_path.exists():
                jasmine_config = ConfigManager.load_config(str(jasmine_config_path))
                return jasmine_config.get('sweep_file', './tools/sweep.latest')
            else:
                return './tools/sweep.latest'
        except:
            return './tools/sweep.latest'
    
    def create_sweep_task(self) -> Dict[str, Any]:
        """Create a wandb sweep task definition"""
        sweep_log_file = self.get_sweep_log_file_from_config()
        
        return {
            "label": "wandb sweep",
            "type": "shell",
            "command": f"(wandb sweep ${{file}} 2>&1) | tee {sweep_log_file}",
            "group": {
                "kind": "build",
                "isDefault": True
            },
            "problemMatcher": []
        }
    
    def install_sweep_task(self, force: bool = False, verbose: bool = False) -> bool:
        """Install wandb sweep task to VS Code tasks.json"""
        try:
            if not self.ensure_vscode_dir():
                return False
            
            print("🔧 Installing wandb sweep task to VS Code...")
            
            # Check if tasks.json exists and load content
            tasks_data = None
            if self.tasks_file.exists():
                file_size = self.tasks_file.stat().st_size
                print(f"📄 Found existing tasks.json: {self.tasks_file} ({file_size} bytes)")
                
                # Load existing tasks.json without modifying other content
                try:
                    with open(self.tasks_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Handle JSON with comments (VS Code style)
                    # Remove single-line comments (// ... )
                    lines = content.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        # Find // that's not inside a string
                        comment_pos = -1
                        in_string = False
                        escape_next = False
                        
                        for i, char in enumerate(line):
                            if escape_next:
                                escape_next = False
                                continue
                            
                            if char == '\\':
                                escape_next = True
                                continue
                            
                            if char == '"' and not escape_next:
                                in_string = not in_string
                                continue
                            
                            if not in_string and char == '/' and i < len(line) - 1 and line[i + 1] == '/':
                                comment_pos = i
                                break
                        
                        if comment_pos >= 0:
                            line = line[:comment_pos].rstrip()
                        
                        cleaned_lines.append(line)
                    
                    cleaned_content = '\n'.join(cleaned_lines)
                    tasks_data = json.loads(cleaned_content)
                    
                    existing_tasks = tasks_data.get('tasks', [])
                    print(f"✅ Successfully loaded {len(existing_tasks)} existing tasks")
                    if verbose and existing_tasks:
                        print("📋 Existing tasks:")
                        for i, task in enumerate(existing_tasks):
                            label = task.get('label', 'Unknown')
                            print(f"   {i+1}. {label}")
                        
                except Exception as e:
                    print(f"⚠ Error loading existing tasks.json: {e}")
                    print("  This might be due to JSON format issues or file corruption")
                    print("  Creating backup and new tasks.json structure")
                    
                    # Create backup of original file
                    backup_path = self.tasks_file.with_suffix('.json.backup')
                    try:
                        import shutil
                        shutil.copy2(self.tasks_file, backup_path)
                        print(f"  📦 Backup created: {backup_path}")
                    except:
                        print("  ⚠ Could not create backup")
                    
                    tasks_data = None
            else:
                if verbose:
                    print("📄 No existing tasks.json found, will create new one")
            
            # If loading failed or file doesn't exist, create default structure
            if tasks_data is None:
                tasks_data = {
                    "version": "2.0.0",
                    "tasks": []
                }
            
            # Ensure tasks array exists
            if "tasks" not in tasks_data:
                tasks_data["tasks"] = []
            
            # Check if wandb sweep task already exists
            sweep_task_index = -1
            sweep_task_exists = False
            existing_task_label = None
            
            for i, task in enumerate(tasks_data["tasks"]):
                task_label = task.get("label", "")
                if task_label in ["wandb sweep", "JasmineTool: Wandb Sweep"]:
                    sweep_task_exists = True
                    sweep_task_index = i
                    existing_task_label = task_label
                    break
            
            if sweep_task_exists:
                if not force:
                    print(f"ℹ️  Wandb sweep task already exists in tasks.json (label: '{existing_task_label}')")
                    print("  Use --force to overwrite the existing task")
                    if verbose:
                        print(f"📄 Tasks file: {self.tasks_file}")
                    print("❌ Installation cancelled - task already exists")
                    return False  # Exit without doing anything
                else:
                    print(f"🔄 Overwriting existing wandb sweep task (label: '{existing_task_label}')...")
            
            # Create new sweep task
            sweep_task = self.create_sweep_task()
            
            # Add or replace task
            if sweep_task_exists and force:
                # Replace existing task at the same position
                tasks_data["tasks"][sweep_task_index] = sweep_task
                action_taken = "overwritten"
            else:
                # Add new task to the end
                tasks_data["tasks"].append(sweep_task)
                action_taken = "installed"
            
            # Save tasks.json back (preserving all existing content)
            if self.save_tasks(tasks_data):
                if action_taken == "overwritten":
                    print("✅ Wandb sweep task overwritten successfully!")
                else:
                    print("✅ Wandb sweep task installed successfully!")
                
                print(f"📄 Tasks file updated: {self.tasks_file}")
                print(f"📊 Total tasks in file: {len(tasks_data['tasks'])}")
                
                # Get sweep log file for user info
                sweep_log_file = self.get_sweep_log_file_from_config()
                print(f"📝 Sweep output will be logged to: {sweep_log_file}")
                
                print("\n🚀 Usage:")
                print("  1. Open a wandb sweep config file (*.yaml)")
                print("  2. Press Ctrl+Shift+P (or Cmd+Shift+P on Mac)")
                print("  3. Type 'Tasks: Run Task'")
                print("  4. Select 'wandb sweep'")
                print("  5. Or use Ctrl+Shift+R (or Cmd+Shift+R on Mac)")
                return True
            else:
                print("❌ Failed to save tasks.json")
                return False
                
        except Exception as e:
            print(f"✗ Error installing sweep task: {e}")
            return False


def run_sweep(config_path: str, verbose: bool = False) -> bool:
    """Run wandb sweep with configuration file"""
    try:
        manager = SweepManager(config_path)
        return manager.run_wandb_sweep(verbose=verbose)
    except Exception as e:
        print(f"✗ Error running sweep: {e}")
        return False


def install_sweep_task(force: bool = False, verbose: bool = False) -> bool:
    """Install wandb sweep task to VS Code tasks.json"""
    try:
        manager = VSCodeTasksManager()
        return manager.install_sweep_task(force=force, verbose=verbose)
    except Exception as e:
        print(f"✗ Error installing sweep task: {e}")
        return False 