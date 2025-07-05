#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Install Module

This module provides functionality to install JasmineTool commands into VS Code tasks.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from .utils import ConfigManager


class VSCodeTasksManager:
    """Handle VS Code tasks.json integration for JasmineTool"""
    
    def __init__(self):
        """Initialize VS Code tasks manager"""
        self.vscode_dir = Path(".vscode")
        self.tasks_file = self.vscode_dir / "tasks.json"
    
    def normalize_config_path(self, config_path: str) -> str:
        """
        Normalize config path according to rules:
        - Accept absolute paths as-is
        - Accept single filenames and place them in .jasminetool/
        - Reject relative paths (containing path separators but not absolute)
        """
        path = Path(config_path)
        
        # If it's an absolute path, use it as-is
        if path.is_absolute():
            return str(path)
        
        # If it's a single filename (no path separators), place it in .jasminetool/
        if os.sep not in config_path and '/' not in config_path:
            return str(Path(".jasminetool") / config_path)
        
        # If it's a relative path with path separators, reject it
        raise ValueError(f"Relative paths are not allowed: {config_path}. "
                        f"Use absolute paths or single filenames (will be placed in .jasminetool/)")
    
    def ensure_vscode_dir(self) -> bool:
        """Ensure .vscode directory exists"""
        try:
            self.vscode_dir.mkdir(exist_ok=True)
            return True
        except Exception as e:
            print(f"✗ Error creating .vscode directory: {e}")
            return False
    
    def load_tasks(self) -> Optional[Dict[str, Any]]:
        """Load existing tasks.json file"""
        if not self.tasks_file.exists():
            return None
        
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
            
            return tasks_data
            
        except Exception as e:
            print(f"⚠ Error loading existing tasks.json: {e}")
            return None
    
    def save_tasks(self, tasks: Dict[str, Any]) -> bool:
        """Save tasks.json file"""
        try:
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"✗ Error saving tasks.json: {e}")
            return False
    
    def create_target_task(self, target: str, config_path: str = "config.yaml") -> Dict[str, Any]:
        """Create a JasmineTool target task definition"""
        normalized_path = self.normalize_config_path(config_path)
        
        return {
            "label": f"sweep {target}",
            "type": "shell",
            "command": f"jt -t {target} sync && jt -t {target} start",
            "options": {
                "cwd": "${workspaceFolder}"
            },
            "group": {
                "kind": "build",
                "isDefault": False
            },
            "problemMatcher": [],
            "presentation": {
                "echo": True,
                "reveal": "always",
                "focus": False,
                "panel": "shared",
                "showReuseMessage": True,
                "clear": False
            }
        }
    
    def get_target_list(self, config_path: str) -> List[str]:
        """Get list of available targets from configuration"""
        try:
            normalized_path = self.normalize_config_path(config_path)
            config = ConfigManager.load_config(normalized_path)
            if not config:
                return []
            
            targets = []
            for key, value in config.items():
                # Skip non-target entries (comments, global settings)
                if key.startswith("#") or key in ["sweep_file", "pattern", "src_dir", "pre_commands"]:
                    continue
                if isinstance(value, dict):
                    targets.append(key)
            
            return targets
        except Exception as e:
            print(f"✗ Error getting target list: {e}")
            return []
    
    def install_target_tasks(self, config_path: str, targets: Optional[List[str]] = None, force: bool = False, verbose: bool = False) -> bool:
        """Install JasmineTool target tasks to VS Code tasks.json"""
        try:
            if not self.ensure_vscode_dir():
                return False
            
            print("🔧 Installing JasmineTool target tasks to VS Code...")
            
            # Normalize and validate config path
            try:
                normalized_path = self.normalize_config_path(config_path)
                print(f"📁 Using config file: {normalized_path}")
            except ValueError as e:
                print(f"❌ Invalid config path: {e}")
                return False
            
            # Get target list
            if targets is None:
                targets = self.get_target_list(config_path)
            
            if not targets:
                print("❌ No targets found in configuration")
                return False
            
            print(f"📋 Found {len(targets)} target(s): {', '.join(targets)}")
            
            # Load existing tasks
            tasks_data = self.load_tasks()
            if tasks_data is None:
                print("📄 No existing tasks.json found, creating new one")
                tasks_data = {
                    "version": "2.0.0",
                    "tasks": []
                }
            else:
                file_size = self.tasks_file.stat().st_size
                existing_tasks = tasks_data.get('tasks', [])
                print(f"📄 Found existing tasks.json: {self.tasks_file} ({file_size} bytes)")
                print(f"✅ Successfully loaded {len(existing_tasks)} existing tasks")
                
                if verbose and existing_tasks:
                    print("📋 Existing tasks:")
                    for i, task in enumerate(existing_tasks):
                        label = task.get('label', 'Unknown')
                        print(f"   {i+1}. {label}")
            
            # Ensure tasks array exists
            if "tasks" not in tasks_data:
                tasks_data["tasks"] = []
            
            # Process each target
            installed_count = 0
            overwritten_count = 0
            skipped_count = 0
            
            for target in targets:
                task_label = f"sweep {target}"
                
                # Check if task already exists
                existing_task_index = -1
                for i, task in enumerate(tasks_data["tasks"]):
                    if task.get("label") == task_label:
                        existing_task_index = i
                        break
                
                if existing_task_index >= 0:
                    if not force:
                        print(f"ℹ️  Task '{task_label}' already exists, skipping")
                        skipped_count += 1
                        continue
                    else:
                        print(f"🔄 Overwriting existing task '{task_label}'")
                        tasks_data["tasks"][existing_task_index] = self.create_target_task(target, config_path)
                        overwritten_count += 1
                else:
                    print(f"➕ Installing task '{task_label}'")
                    tasks_data["tasks"].append(self.create_target_task(target, config_path))
                    installed_count += 1
            
            # Save tasks.json
            if self.save_tasks(tasks_data):
                print(f"✅ Tasks installation completed!")
                print(f"📄 Tasks file updated: {self.tasks_file}")
                print(f"📊 Total tasks in file: {len(tasks_data['tasks'])}")
                
                if installed_count > 0:
                    print(f"➕ New tasks installed: {installed_count}")
                if overwritten_count > 0:
                    print(f"🔄 Tasks overwritten: {overwritten_count}")
                if skipped_count > 0:
                    print(f"⏭️  Tasks skipped: {skipped_count}")
                
                print("\n🚀 Usage:")
                print("  1. Press Ctrl+Shift+P (or Cmd+Shift+P on Mac)")
                print("  2. Type 'Tasks: Run Task'")
                print("  3. Select one of the installed tasks:")
                for target in targets:
                    print(f"     - sweep {target}")
                print("  4. Or use Ctrl+Shift+R (or Cmd+Shift+R on Mac)")
                
                return True
            else:
                print("❌ Failed to save tasks.json")
                return False
                
        except Exception as e:
            print(f"✗ Error installing target tasks: {e}")
            return False


def install_target_tasks(config_path: str, targets: Optional[List[str]] = None, force: bool = False, verbose: bool = False) -> bool:
    """Install JasmineTool target tasks to VS Code tasks.json"""
    try:
        manager = VSCodeTasksManager()
        return manager.install_target_tasks(config_path, targets, force, verbose)
    except Exception as e:
        print(f"✗ Error installing target tasks: {e}")
        return False 