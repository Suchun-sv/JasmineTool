#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified Task Runner

Main runner class for the JasmineTool system.
"""

import sys
import os
import subprocess
import yaml
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

from .execution_modes import LocalMode, RemoteMode, SlurmMode, RemoteGpuMode
from .utils import ConfigManager, GitManager, CommandExtractor, PreCommandExecutor, TimeoutInput


class UnifiedTaskRunner:
    """Main task runner class that coordinates different execution modes"""
    
    def __init__(self, config_path: str = './.jasminetool/config.yaml'):
        """Initialize the task runner with configuration path"""
        self.config_path = config_path
        self.config = None
        self.execution_modes = {
            'local': LocalMode(),
            'remote': RemoteMode(),
            'slurm': SlurmMode(),
            'remote_gpu': RemoteGpuMode()
        }
    
    def load_configuration(self) -> bool:
        """Load configuration from YAML file"""
        try:
            self.config = ConfigManager.load_config(self.config_path)
            return True
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
    
    def save_configuration(self) -> bool:
        """Save current configuration to YAML file"""
        if self.config is None:
            print("No configuration to save")
            return False
        
        try:
            return ConfigManager.save_config(self.config, self.config_path)
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def validate_target(self, target: str) -> bool:
        """Validate if target exists in configuration"""
        if self.config is None:
            print("Configuration not loaded")
            return False
        
        return target in self.config
    
    def get_sweep_command(self) -> Optional[str]:
        """Get sweep command from configuration"""
        if self.config is None:
            return None
        
        sweep_file = self.config.get('sweep_file', '')
        pattern = self.config.get('pattern', '')
        
        if not sweep_file or not pattern:
            return None
        
        return CommandExtractor.get_sweep_command(sweep_file, pattern)
    
    def confirm_execution(self, command: str) -> bool:
        """Confirm command execution with user"""
        print(f"Command to execute: {command}")
        confirmation = input("Do you want to proceed? (y/n): ").lower()
        return confirmation == 'y'
    
    def interactive_config_update(self, target_config: Dict[str, Any]) -> None:
        """Interactively update target configuration"""
        timeout_input = TimeoutInput(timeout=3)
        
        print("=== Interactive Configuration Update ===")
        print("Press Enter to keep current value, or type new value:")
        
        # Update basic settings
        for key in ['gpu_config', 'num_processes']:
            if key in target_config:
                current_value = target_config[key]
                new_value = timeout_input.get_input(f"{key} (current: {current_value})", str(current_value))
                
                if key == 'num_processes':
                    try:
                        target_config[key] = int(new_value)
                    except ValueError:
                        print(f"Invalid number for {key}, keeping current value")
                else:
                    target_config[key] = new_value
        
        # Update mode-specific settings
        if 'ssh_host' in target_config:
            ssh_host = timeout_input.get_input(f"ssh_host (current: {target_config['ssh_host']})", 
                                             target_config['ssh_host'])
            target_config['ssh_host'] = ssh_host
        
        if 'work_dir' in target_config:
            work_dir = timeout_input.get_input(f"work_dir (current: {target_config['work_dir']})", 
                                             target_config['work_dir'])
            target_config['work_dir'] = work_dir
    
    def prepare_git_environment(self, target_config: Dict[str, Any]) -> Optional[str]:
        """Prepare git environment and return current branch"""
        if target_config.get('sync_method') == 'git':
            git_dir = target_config.get('git_dir', '.')
            
            if not GitManager.check_git_status(git_dir):
                print("Git repository has uncommitted changes")
                return None
            
            return GitManager.get_current_branch(git_dir)
        
        return None
    
    def execute_pre_commands(self, target_config: Dict[str, Any]) -> bool:
        """Execute pre-commands if configured"""
        if 'pre_commands' in target_config:
            return PreCommandExecutor.execute_pre_commands(target_config['pre_commands'])
        return True
    
    def execute_target(self, target: str, skip_confirmation: bool = False, skip_interactive: bool = False) -> bool:
        """Execute the specified target"""
        if not self.validate_target(target):
            print(f"Target '{target}' not found in configuration")
            return False
        
        # Get target configuration
        if self.config is None:
            print("Configuration not loaded")
            return False
        
        target_config = self.config[target].copy()
        
        # Interactive configuration update
        if not skip_interactive:
            self.interactive_config_update(target_config)
        
        # Get sweep command
        command = self.get_sweep_command()
        if not command:
            print("Could not extract sweep command")
            return False
        
        # Confirmation
        if not skip_confirmation and not self.confirm_execution(command):
            print("Execution cancelled")
            return False
        
        # Prepare git environment
        current_branch = self.prepare_git_environment(target_config)
        
        # Execute pre-commands
        if not self.execute_pre_commands(target_config):
            print("Pre-commands failed")
            return False
        
        # Get execution mode
        mode = target_config.get('mode', 'local')
        if mode not in self.execution_modes:
            print(f"Unknown execution mode: {mode}")
            return False
        
        # Execute the target
        print(f"Executing target '{target}' in '{mode}' mode")
        execution_mode = self.execution_modes[mode]
        
        return execution_mode.execute(target_config, command, current_branch=current_branch)


def main():
    """Main entry point for the command line interface"""
    parser = argparse.ArgumentParser(description='Unified Task Runner')
    parser.add_argument('target', help='Target configuration to execute')
    parser.add_argument('--config', default='./.jasminetool/config.yaml', 
                       help='Path to configuration file')
    parser.add_argument('--skip-confirmation', action='store_true',
                       help='Skip execution confirmation')
    parser.add_argument('--skip-interactive', action='store_true',
                       help='Skip interactive configuration update')
    
    args = parser.parse_args()
    
    # Create and run the task runner
    runner = UnifiedTaskRunner(args.config)
    
    if not runner.load_configuration():
        sys.exit(1)
    
    success = runner.execute_target(
        args.target, 
        skip_confirmation=args.skip_confirmation,
        skip_interactive=args.skip_interactive
    )
    
    if not success:
        sys.exit(1)
    
    print("Task completed successfully!")


if __name__ == '__main__':
    main() 