#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration Display Module

This module provides functionality to display configuration files in a beautiful format.
"""

import os
import sys
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from .utils import ConfigManager


class ConfigDisplayer:
    """Handle configuration display with beautiful formatting"""
    
    def __init__(self, config_path: str):
        """Initialize with configuration path"""
        self.config_path = Path(config_path)
        self.config: Optional[Dict[str, Any]] = None
    
    def load_config(self) -> bool:
        """Load configuration from file"""
        try:
            if not self.config_path.exists():
                print(f"✗ Configuration file not found: {self.config_path}")
                print("  Use 'jasminetool init' to create a default configuration")
                return False
            
            self.config = ConfigManager.load_config(str(self.config_path))
            return True
        except Exception as e:
            print(f"✗ Error loading configuration: {e}")
            return False
    
    def display_header(self) -> None:
        """Display header information"""
        print("🔧 JasmineTool Configuration")
        print("=" * 60)
        print(f"📄 Configuration file: {self.config_path}")
        print(f"📁 File size: {self.config_path.stat().st_size} bytes")
        
        # Format modification time
        mtime = self.config_path.stat().st_mtime
        formatted_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"🕒 Last modified: {formatted_time}")
        print("=" * 60)
        print()
    
    def display_section(self, title: str, content: Any, indent: int = 0) -> None:
        """Display a configuration section with proper formatting"""
        indent_str = "  " * indent
        
        if isinstance(content, dict):
            print(f"{indent_str}📦 {title}")
            for key, value in content.items():
                if key.startswith("#"):
                    # Skip comment keys
                    continue
                
                if isinstance(value, dict):
                    self.display_section(f"{key}", value, indent + 1)
                elif isinstance(value, list):
                    print(f"{indent_str}  📋 {key}:")
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            print(f"{indent_str}    [{i}]:")
                            for sub_key, sub_value in item.items():
                                print(f"{indent_str}      {sub_key}: {sub_value}")
                        else:
                            print(f"{indent_str}    - {item}")
                else:
                    if isinstance(value, str):
                        # Highlight important values
                        if any(keyword in key.lower() for keyword in ['url', 'host', 'path', 'dir']):
                            print(f"{indent_str}  🔗 {key}: {value}")
                        elif any(keyword in key.lower() for keyword in ['mode', 'runner', 'command']):
                            print(f"{indent_str}  ⚙️  {key}: {value}")
                        else:
                            print(f"{indent_str}  📝 {key}: {value}")
                    else:
                        print(f"{indent_str}  🔢 {key}: {value}")
        else:
            print(f"{indent_str}📋 {title}: {content}")
    
    def display_targets(self) -> None:
        """Display target configurations"""
        if not self.config:
            return
        
        print("🎯 Target Configurations")
        print("-" * 40)
        
        target_count = 0
        for key, value in self.config.items():
            if isinstance(value, dict) and not key.startswith("#"):
                # Skip non-target configurations
                if key in ['sweep_file', 'pattern', 'src_dir', 'pre_commands']:
                    continue
                
                target_count += 1
                print(f"\n{target_count}. {key}")
                print("   " + "-" * 20)
                
                # Display target details
                mode = value.get('mode', 'N/A')
                print(f"   Mode: {mode}")
                
                if 'ssh_host' in value:
                    print(f"   SSH Host: {value['ssh_host']}")
                
                if 'github_url' in value:
                    print(f"   GitHub URL: {value['github_url']}")
                
                if 'work_dir' in value:
                    print(f"   Work Directory: {value['work_dir']}")
                
                if 'gpu_config' in value:
                    print(f"   GPU Config: {value['gpu_config']}")
                
                if 'num_processes' in value:
                    print(f"   Processes: {value['num_processes']}")
                
                if 'dvc_cache' in value:
                    print(f"   DVC Cache: {value['dvc_cache']}")
                
                if 'dvc_remote' in value:
                    print(f"   DVC Remote: {value['dvc_remote']}")
                
                if 'command_runner' in value:
                    print(f"   Command Runner: {value['command_runner']}")
        
        if target_count == 0:
            print("   No target configurations found")
    
    def display_global_settings(self) -> None:
        """Display global settings"""
        if not self.config:
            return
        
        print("🌍 Global Settings")
        print("-" * 40)
        
        global_settings = ['sweep_file', 'pattern', 'src_dir']
        found_settings = False
        
        for setting in global_settings:
            if setting in self.config:
                found_settings = True
                value = self.config[setting]
                print(f"   {setting}: {value}")
        
        if not found_settings:
            print("   No global settings found")
    
    def display_pre_commands(self) -> None:
        """Display pre-commands configuration"""
        if not self.config or 'pre_commands' not in self.config:
            return
        
        print("\n🔧 Pre-Commands")
        print("-" * 40)
        
        pre_commands = self.config['pre_commands']
        if isinstance(pre_commands, list):
            for i, cmd in enumerate(pre_commands, 1):
                print(f"   {i}. {cmd}")
        else:
            print("   Invalid pre-commands format")
    
    def display_summary(self) -> None:
        """Display configuration summary"""
        if not self.config:
            return
        
        print("\n📊 Configuration Summary")
        print("-" * 40)
        
        target_count = 0
        modes = {}
        
        for key, value in self.config.items():
            if isinstance(value, dict) and not key.startswith("#"):
                # Skip non-target configurations
                if key in ['sweep_file', 'pattern', 'src_dir', 'pre_commands']:
                    continue
                
                target_count += 1
                mode = value.get('mode', 'unknown')
                modes[mode] = modes.get(mode, 0) + 1
        
        print(f"   Total targets: {target_count}")
        if modes:
            print("   Modes breakdown:")
            for mode, count in modes.items():
                print(f"     - {mode}: {count}")
        
        print(f"   Configuration file size: {self.config_path.stat().st_size} bytes")
    
    def display_target_config(self, target: str, verbose: bool = False) -> None:
        """Display configuration for a specific target"""
        if not self.config:
            return
        
        print(f"🎯 Target Configuration: {target}")
        print("=" * 60)
        print(f"📄 Configuration file: {self.config_path}")
        
        # Format modification time
        mtime = self.config_path.stat().st_mtime
        formatted_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"🕒 Last modified: {formatted_time}")
        print("=" * 60)
        print()
        
        # Check if target exists
        if target not in self.config:
            print(f"❌ Target '{target}' not found in configuration")
            print("\n🔍 Available targets:")
            available_targets = []
            for key, value in self.config.items():
                if isinstance(value, dict) and not key.startswith("#"):
                    if key not in ['sweep_file', 'pattern', 'src_dir', 'pre_commands']:
                        available_targets.append(key)
            
            if available_targets:
                for i, available_target in enumerate(available_targets, 1):
                    print(f"   {i}. {available_target}")
            else:
                print("   No targets found in configuration")
            return
        
        target_config = self.config[target]
        
        # Display target details
        print(f"📋 Target Details")
        print("-" * 40)
        
        # Display in organized sections
        essential_keys = ['mode', 'ssh_host', 'github_url', 'work_dir']
        gpu_keys = ['gpu_config', 'num_processes']
        dvc_keys = ['dvc_cache', 'dvc_remote', 'command_runner']
        other_keys = []
        
        for key in target_config:
            if key not in essential_keys + gpu_keys + dvc_keys:
                other_keys.append(key)
        
        # Essential Configuration
        print("🔧 Essential Configuration:")
        for key in essential_keys:
            if key in target_config:
                value = target_config[key]
                if key == 'mode':
                    print(f"   ⚙️  {key}: {value}")
                elif key in ['ssh_host', 'github_url', 'work_dir']:
                    print(f"   🔗 {key}: {value}")
                else:
                    print(f"   📝 {key}: {value}")
        
        # GPU Configuration
        if any(key in target_config for key in gpu_keys):
            print("\n🖥️  GPU Configuration:")
            for key in gpu_keys:
                if key in target_config:
                    value = target_config[key]
                    print(f"   🔢 {key}: {value}")
        
        # DVC Configuration
        if any(key in target_config for key in dvc_keys):
            print("\n📦 DVC Configuration:")
            for key in dvc_keys:
                if key in target_config:
                    value = target_config[key]
                    if key == 'command_runner':
                        print(f"   ⚙️  {key}: {value}")
                    else:
                        print(f"   🔗 {key}: {value}")
        
        # Other Configuration
        if other_keys:
            print("\n🔧 Other Configuration:")
            for key in other_keys:
                value = target_config[key]
                if isinstance(value, dict):
                    print(f"   📦 {key}:")
                    for sub_key, sub_value in value.items():
                        print(f"      {sub_key}: {sub_value}")
                elif isinstance(value, list):
                    print(f"   📋 {key}:")
                    for item in value:
                        print(f"      - {item}")
                else:
                    print(f"   📝 {key}: {value}")
        
        # Display relevant global settings
        print("\n🌍 Related Global Settings:")
        print("-" * 40)
        global_settings = ['sweep_file', 'pattern', 'src_dir']
        for setting in global_settings:
            if setting in self.config:
                value = self.config[setting]
                print(f"   {setting}: {value}")
        
        # Display raw YAML for this target if verbose
        if verbose:
            print(f"\n🔍 Raw YAML for target '{target}':")
            print("-" * 40)
            try:
                import yaml
                target_yaml = yaml.dump({target: target_config}, default_flow_style=False, sort_keys=False)
                print(target_yaml)
            except Exception as e:
                print(f"Error displaying raw YAML: {e}")
    
    def display_config(self, target: Optional[str] = None, verbose: bool = False) -> bool:
        """Display the complete configuration"""
        try:
            if not self.load_config():
                return False
            
            if target:
                # Display only specific target
                self.display_target_config(target, verbose)
            else:
                # Display all configuration
                self.display_header()
                self.display_global_settings()
                self.display_targets()
                self.display_pre_commands()
                self.display_summary()
                
                if verbose:
                    print("\n🔍 Raw Configuration (YAML)")
                    print("=" * 60)
                    try:
                        with open(self.config_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Remove comment lines that start with #
                            lines = content.split('\n')
                            filtered_lines = []
                            for line in lines:
                                if line.strip().startswith('#') and ':' not in line:
                                    continue
                                filtered_lines.append(line)
                            
                            print('\n'.join(filtered_lines))
                    except Exception as e:
                        print(f"Error reading raw config: {e}")
            
            print("\n" + "=" * 60)
            print("✅ Configuration display completed successfully!")
            return True
            
        except Exception as e:
            print(f"✗ Error displaying configuration: {e}")
            return False


def display_config(config_path: str, target: Optional[str] = None, verbose: bool = False) -> bool:
    """Display configuration file with beautiful formatting"""
    displayer = ConfigDisplayer(config_path)
    return displayer.display_config(target=target, verbose=verbose) 