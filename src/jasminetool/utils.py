#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utilities

Utility classes and functions for the JasmineTool system.
"""

import os
import subprocess
import yaml
import signal
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class TimeoutInput:
    """Input with timeout functionality"""
    
    def __init__(self, timeout: int = 3):
        self.timeout = timeout
        self.input_received = False
        self.input_value = ""
    
    def _timeout_handler(self, signum, frame):
        """Handle timeout signal"""
        pass
    
    def get_input(self, prompt: str, default: str = "") -> str:
        """Get input with timeout, return default if timeout"""
        print(f"{prompt} (default: {default}, timeout: {self.timeout}s): ", end="", flush=True)
        
        # Set up signal handler for timeout
        old_handler = signal.signal(signal.SIGALRM, self._timeout_handler)
        signal.alarm(self.timeout)
        
        try:
            result = input()
            signal.alarm(0)  # Cancel the alarm
            return result.strip() if result.strip() else default
        except:
            signal.alarm(0)  # Cancel the alarm
            print(f"\nTimeout! Using default: {default}")
            return default
        finally:
            signal.signal(signal.SIGALRM, old_handler)


class TmuxManager:
    """Tmux session management for running multiple processes"""
    
    @staticmethod
    def extract_sweep_id(command: str) -> str:
        """Extract sweep ID from wandb command"""
        match = re.search(r'([^/]+)$', command)
        return match.group(1) if match else "unknown"
    
    @staticmethod
    def expand_gpu_config(gpu_config: str) -> List[str]:
        """Expand GPU configuration string to list of GPU IDs"""
        if not gpu_config or gpu_config == "":
            return [""]
        
        # If gpu_config is "0" (single GPU), use all available GPUs
        if gpu_config == "0":
            try:
                result = subprocess.run(['nvidia-smi', '--query-gpu=count', '--format=csv,noheader'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    gpu_count_output = result.stdout.strip()
                    if gpu_count_output:
                        num_gpus = len(gpu_count_output.split('\n'))
                        if num_gpus > 0:
                            print(f"🖥️  Detected {num_gpus} GPU(s)")
                            return [str(i) for i in range(num_gpus)]
                print("⚠️  nvidia-smi failed or no GPUs detected, using default GPU 0")
                return ["0"]
            except FileNotFoundError:
                print("⚠️  nvidia-smi not found (no GPU or driver not installed), using CPU-only mode")
                return ["0"]
            except Exception as e:
                print(f"⚠️  Failed to get GPU count: {e}, using default GPU 0")
                return ["0"]
        
        # Parse comma-separated GPU IDs
        gpu_list = [gpu.strip() for gpu in gpu_config.split(',')]
        print(f"🖥️  Using configured GPUs: {gpu_list}")
        return gpu_list
    
    @staticmethod
    def create_tmux_session(gpu_config: str, num_processes: int, command: str, 
                           remote: bool = False) -> str:
        """Create tmux session with multiple processes"""
        sweep_id = TmuxManager.extract_sweep_id(command)
        current_time = datetime.now().strftime("%m%d%H%M")
        session_name = f"{sweep_id}_{current_time}"
        
        print(f"Creating tmux session: {session_name}")
        print(f"Extracted sweep_id: {sweep_id}")
        
        gpu_ids = TmuxManager.expand_gpu_config(gpu_config)
        
        # Check if nvidia-smi is available
        has_nvidia_smi = False
        if not remote:  # Only check locally
            try:
                result = subprocess.run(['nvidia-smi', '--version'], capture_output=True)
                has_nvidia_smi = (result.returncode == 0)
            except FileNotFoundError:
                has_nvidia_smi = False
        else:
            # For remote, assume we'll check in the script
            has_nvidia_smi = True
        
        # Create new tmux session
        tmux_commands = []
        tmux_commands.append(f'tmux new-session -d -s "{session_name}"')
        
        first_pane = True
        for gpu_id in gpu_ids:
            for i in range(num_processes):
                if not first_pane:
                    tmux_commands.append(f'tmux split-window -t "{session_name}"')
                    tmux_commands.append(f'tmux select-layout -t "{session_name}" tiled')
                
                # Build the full command
                env_setup = "source ~/.bashrc && conda activate vector && export WANDB_API_KEY=c1452b5bae77778a04b9cad2a8d96d4424088383"
                
                # Only set CUDA_VISIBLE_DEVICES if we have GPU support and a valid GPU ID
                if has_nvidia_smi and gpu_id and gpu_id != "":
                    cuda_env = f"CUDA_VISIBLE_DEVICES={gpu_id}"
                    full_command = f"{env_setup} && {cuda_env} {command}"
                    print(f"Started process {i} on GPU {gpu_id} in tmux session {session_name}")
                else:
                    full_command = f"{env_setup} && {command}"
                    if has_nvidia_smi:
                        print(f"Started process {i} (CPU mode) in tmux session {session_name}")
                    else:
                        print(f"Started process {i} (no GPU detected) in tmux session {session_name}")
                
                tmux_commands.append(f'tmux send-keys -t "{session_name}" "{full_command}" C-m')
                
                first_pane = False
        
        # Execute all tmux commands
        full_script = ' && '.join(tmux_commands)
        
        if remote:
            return full_script
        else:
            result = subprocess.run(full_script, shell=True)
            if result.returncode == 0:
                print(f"All processes started in session {session_name}")
                return session_name
            else:
                print(f"Failed to create tmux session")
                return ""


class ConfigManager:
    """Configuration management utilities"""
    
    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    
    @staticmethod
    def save_config(config: Dict[str, Any], config_path: str) -> bool:
        """Save configuration to YAML file"""
        try:
            # Create directory if it doesn't exist
            config_dir = os.path.dirname(config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as file:
                yaml.safe_dump(config, file, default_flow_style=False, allow_unicode=True)
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False


class GitManager:
    """Git management utilities"""
    
    @staticmethod
    def check_git_status(git_dir: str) -> bool:
        """Check if git repository is clean"""
        try:
            # Check if there are any uncommitted changes
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  cwd=git_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                return False
            
            # If output is empty, repository is clean
            return len(result.stdout.strip()) == 0
        except:
            return False
    
    @staticmethod
    def get_current_branch(git_dir: str) -> str:
        """Get current git branch"""
        try:
            result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                                  cwd=git_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "main"
        except:
            return "main"


class CommandExtractor:
    """Command extraction utilities"""
    
    @staticmethod
    def get_sweep_command(sweep_file: str, pattern: str) -> str:
        """Extract sweep command from file using pattern"""
        if not os.path.exists(sweep_file):
            raise FileNotFoundError(f"Sweep file not found: {sweep_file}")
        
        with open(sweep_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Simple pattern matching - can be enhanced
        if pattern in content:
            # Extract the line containing the pattern
            lines = content.split('\n')
            for line in lines:
                if pattern in line:
                    return line.strip()
        
        raise ValueError(f"Pattern '{pattern}' not found in {sweep_file}")


class PreCommandExecutor:
    """Pre-command execution utilities"""
    
    @staticmethod
    def execute_pre_commands(pre_commands: List[Dict[str, Any]]) -> bool:
        """Execute pre-commands in sequence"""
        for cmd_config in pre_commands:
            if not PreCommandExecutor._execute_single_command(cmd_config):
                return False
        return True
    
    @staticmethod
    def _execute_single_command(cmd_config: Dict[str, Any]) -> bool:
        """Execute a single pre-command"""
        command = cmd_config.get('command', '')
        if not command:
            return True
        
        working_dir = cmd_config.get('working_dir', '.')
        
        print(f"Executing pre-command: {command}")
        
        try:
            result = subprocess.run(command, shell=True, cwd=working_dir, 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Pre-command executed successfully")
                if result.stdout:
                    print(f"Output: {result.stdout}")
                return True
            else:
                print(f"Pre-command failed with return code {result.returncode}")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                return False
        except Exception as e:
            print(f"Error executing pre-command: {e}")
            return False 