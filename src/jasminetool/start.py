#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Start Module for JasmineTool

This module provides functionality to start wandb agents in tmux sessions
for a given target configuration.
"""

import os
import sys
import subprocess
import time
import threading
import signal
import select
import termios
import tty
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path

from .utils import ConfigManager
from .ssh_executor import RemoteTargetExecutor


class StartManager:
    """Manages the start operation for wandb agents"""
    
    def __init__(self, config_path: str, target: str, verbose: bool = False):
        self.config_path = Path(config_path).resolve()
        self.config_dir = self.config_path.parent
        self.target = target
        self.verbose = verbose
        self.config = None
        self.target_config = None
        self.original_cwd = Path.cwd()
        self.work_dir = None
        
    def load_config(self) -> bool:
        """Load configuration from file"""
        try:
            self.config = ConfigManager.load_config(str(self.config_path))
            if not self.config:
                print("❌ Failed to load configuration")
                return False
            
            if self.verbose:
                print(f"✅ Loaded configuration from: {self.config_path}")
            
            return True
        except Exception as e:
            print(f"❌ Failed to load configuration: {e}")
            return False
    
    def validate_target(self) -> bool:
        """Validate target configuration"""
        if not self.config:
            print("❌ Configuration not loaded")
            return False
            
        if self.target not in self.config:
            print(f"❌ Target '{self.target}' not found in configuration")
            # Show available targets (exclude non-target keys)
            exclude_keys = {'pattern', 'pre_commands', 'src_dir', 'sweep_file', 'command_runner', 'wandb_key'}
            available_targets = [k for k in self.config.keys() if k not in exclude_keys and isinstance(self.config[k], dict)]
            if available_targets:
                print(f"Available targets: {', '.join(available_targets)}")
            return False
        
        self.target_config = self.config[self.target]
        
        # Get work directory
        if not self.target_config:
            print(f"❌ Target configuration not loaded")
            return False
            
        work_dir = self.target_config.get("work_dir")
        if not work_dir:
            print(f"❌ No work_dir specified for target '{self.target}'")
            return False
        
        self.work_dir = Path(work_dir).expanduser().resolve()
        
        if self.verbose:
            print(f"📁 Work directory: {self.work_dir}")
        
        # Check if work directory exists
        if not self.work_dir.exists():
            print(f"❌ Work directory does not exist: {self.work_dir}")
            return False
        
        return True
    
    def extract_sweep_id_from_file(self) -> Optional[str]:
        """Extract wandb sweep ID from sweep file"""
        if not self.config:
            print("❌ Configuration not loaded")
            return None
            
        sweep_file_path_str = self.config.get('sweep_file', 'sweep_config.yaml')
        sweep_file_path = Path(sweep_file_path_str)
        
        # Check path type and handle accordingly
        if sweep_file_path.is_absolute():
            # Absolute path - use as is
            if self.verbose:
                print(f"📄 Using absolute path: {sweep_file_path}")
        elif '/' in sweep_file_path_str or '\\' in sweep_file_path_str:
            # Contains path separators - check if it's an allowed relative path
            if sweep_file_path_str.startswith('.jasminetool/') or sweep_file_path_str.startswith('./jasminetool/'):
                # Special case: allow .jasminetool/ paths, resolve relative to config directory
                sweep_file_path_str = sweep_file_path_str.replace('.jasminetool/', '')
                sweep_file_path = self.config_dir / sweep_file_path_str
                if self.verbose:
                    print(f"📄 Using .jasminetool/ relative path: {sweep_file_path}")
            else:
                # Other relative paths are not allowed
                print(f"❌ Relative paths are not allowed for sweep_file: {sweep_file_path_str}")
                print("   Please use either:")
                print("   - Just the filename (will be placed in .jasminetool/)")
                print("   - An absolute path")
                print("   - A path starting with .jasminetool/")
                print("   Examples:")
                print("     sweep_file: sweep_config.yaml                    # -> .jasminetool/sweep_config.yaml")
                print("     sweep_file: .jasminetool/sweep_config.yaml       # -> .jasminetool/sweep_config.yaml")
                print("     sweep_file: /path/to/your/sweep_config.yaml     # -> /path/to/your/sweep_config.yaml")
                return None
        else:
            # Just a filename - place in .jasminetool/
            sweep_file_path = self.config_dir / sweep_file_path_str
            if self.verbose:
                print(f"📄 Using filename in .jasminetool/: {sweep_file_path}")
        
        if self.verbose:
            print(f"📄 Looking for sweep file: {sweep_file_path}")
        
        if not sweep_file_path.exists():
            print(f"❌ Sweep file not found: {sweep_file_path}")
            return None
        
        try:
            with open(sweep_file_path, 'r') as f:
                content = f.read()
            
            if self.verbose:
                print(f"📄 Reading sweep file: {sweep_file_path}")
            
            # Look for the line with "wandb agent"
            lines = content.strip().split('\n')
            for line in lines:
                if 'wandb agent' in line and 'Run sweep agent with:' in line:
                    # Extract the sweep ID from the line
                    # Format: "wandb: Run sweep agent with: wandb agent yangbn/JasmineTool/ciwmshft"
                    parts = line.split('wandb agent')
                    if len(parts) > 1:
                        sweep_id = parts[-1].strip()
                        if self.verbose:
                            print(f"✅ Found sweep ID: {sweep_id}")
                        return sweep_id
            
            print(f"❌ Could not find sweep ID in file: {sweep_file_path}")
            print("Expected format: 'wandb: Run sweep agent with: wandb agent owner/project/sweep_id'")
            return None
            
        except Exception as e:
            print(f"❌ Error reading sweep file: {e}")
            return None
    
    def get_wandb_key(self) -> Optional[str]:
        """Get wandb key from various sources with priority"""
        if not self.config or not self.target_config:
            print("❌ Configuration not loaded")
            return None
            
        if self.verbose:
            print("🔑 Getting wandb API key...")
        
        # Check target specific wandb_key
        if "wandb_key" in self.target_config:
            if self.verbose:
                print("✅ Using wandb_key from target configuration")
            return self.target_config["wandb_key"]
        
        # Check global wandb_key
        if "wandb_key" in self.config:
            if self.verbose:
                print("✅ Using wandb_key from global configuration")
            return self.config["wandb_key"]
        
        # Check environment variable
        wandb_key = os.environ.get("WANDB_API_KEY")
        if wandb_key:
            if self.verbose:
                print("✅ Using wandb_key from environment variable")
            return wandb_key
        
        # Ask user for wandb key
        print("🔑 WANDB API key not found in configuration or environment")
        print("You can get your API key from: https://wandb.ai/authorize")
        
        while True:
            try:
                wandb_key = input("Please enter your WANDB API key: ").strip()
                if wandb_key:
                    break
                print("❌ Key cannot be empty. Please try again.")
            except KeyboardInterrupt:
                print("\n❌ Operation cancelled by user")
                return None
        
        # Ask if user wants to persist the key
        while True:
            try:
                persist = input("Do you want to save this key to config.yaml? (y/n): ").strip().lower()
                if persist in ['y', 'yes']:
                    return self.persist_wandb_key(wandb_key)
                elif persist in ['n', 'no']:
                    if self.verbose:
                        print("✅ Using wandb_key for this session only")
                    return wandb_key
                else:
                    print("Please enter 'y' or 'n'")
            except KeyboardInterrupt:
                print("\n❌ Operation cancelled by user")
                return None
    
    def persist_wandb_key(self, wandb_key: str) -> str:
        """Persist wandb key to config.yaml"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Add to global config
            config["wandb_key"] = wandb_key
            
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            if self.verbose:
                print(f"✅ WANDB API key saved to {self.config_path}")
            
            return wandb_key
            
        except Exception as e:
            print(f"❌ Failed to save wandb key: {e}")
            return wandb_key
    
    def get_user_input_with_timeout(self, prompt: str, timeout: float = 3.0) -> Optional[str]:
        """Get user input with timeout"""
        print(f"{prompt} (timeout in {timeout:.0f}s):", end='', flush=True)
        
        # Set up signal handler for timeout
        def timeout_handler(signum, frame):
            raise TimeoutError()
        
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(timeout))
        
        try:
            # Try to get user input
            user_input = input()
            signal.alarm(0)  # Cancel the alarm
            return user_input.strip()
        
        except TimeoutError:
            signal.alarm(0)  # Cancel the alarm
            print()  # Move to next line
            return None
        except KeyboardInterrupt:
            signal.alarm(0)  # Cancel the alarm
            print()  # Move to next line
            raise
        finally:
            signal.signal(signal.SIGALRM, old_handler)
    
    def get_temporary_config(self) -> Dict[str, Any]:
        """Get temporary configuration with 3-second timeout for user input"""
        if not self.target_config:
            print("❌ Target configuration not loaded")
            return {"gpu_config": "0,1,2,3", "num_processes": 1}
            
        default_gpu_config = self.target_config.get("gpu_config", "0,1,2,3")
        default_num_processes = self.target_config.get("num_processes", 1)
        
        print(f"📋 Current configuration:")
        print(f"   gpu_config: {default_gpu_config}")
        print(f"   num_processes: {default_num_processes}")
        print()
        
        # Get GPU configuration
        gpu_input = self.get_user_input_with_timeout(
            f"Enter GPU configuration (default: {default_gpu_config})"
        )
        
        if gpu_input:
            gpu_config = gpu_input
            print(f"✅ Using GPU configuration: {gpu_config}")
        else:
            gpu_config = default_gpu_config
            print(f"⏰ Timeout - using default GPU configuration: {gpu_config}")
        
        # Get number of processes
        num_input = self.get_user_input_with_timeout(
            f"Enter number of processes per GPU (default: {default_num_processes})"
        )
        
        if num_input:
            try:
                num_processes = int(num_input)
                print(f"✅ Using number of processes: {num_processes}")
            except ValueError:
                num_processes = default_num_processes
                print(f"❌ Invalid number - using default: {num_processes}")
        else:
            num_processes = default_num_processes
            print(f"⏰ Timeout - using default number of processes: {num_processes}")
        
        # Check if user wants to persist changes
        if gpu_input or num_input:
            print()
            persist_input = self.get_user_input_with_timeout(
                "Do you want to save these settings to config.yaml? (y/n, default: n)"
            )
            
            if persist_input and persist_input.lower() in ['y', 'yes']:
                try:
                    self.persist_target_config(gpu_config, num_processes)
                except Exception as e:
                    print(f"❌ Failed to persist configuration: {e}")
            else:
                print("✅ Using temporary configuration for this session only")
        
        return {
            "gpu_config": gpu_config,
            "num_processes": num_processes
        }
    
    def persist_target_config(self, gpu_config: str, num_processes: int) -> None:
        """Persist target configuration changes to config.yaml"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Update the target configuration
            if self.target in config and isinstance(config[self.target], dict):
                config[self.target]["gpu_config"] = gpu_config
                config[self.target]["num_processes"] = num_processes
            
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            if self.verbose:
                print(f"✅ Target configuration saved to {self.config_path}")
                
        except Exception as e:
            raise Exception(f"Failed to save target configuration: {e}")
    
    def create_tmux_session(self, gpu_config: str, num_processes: int, wandb_key: str, sweep_id: str) -> bool:
        """Create tmux session with wandb agents"""
        if not self.target_config:
            print("❌ Target configuration not loaded")
            return False
            
        if self.verbose:
            print(f"🖥️  Creating tmux session...")
        
        # Parse GPU configuration
        if gpu_config == "0":
            # Use all available GPUs
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=count", "--format=csv,noheader"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    num_gpus = int(result.stdout.strip())
                    if num_gpus > 0:
                        gpu_ids = list(range(num_gpus))
                        print(f"🖥️  Detected {num_gpus} GPU(s): {gpu_ids}")
                    else:
                        gpu_ids = [0]
                        print("⚠️  No GPUs detected, using default GPU 0")
                else:
                    gpu_ids = [0]
                    print("⚠️  nvidia-smi failed, using default GPU 0")
            except FileNotFoundError:
                gpu_ids = [0]
                print("⚠️  nvidia-smi not found (no GPU or driver not installed), using CPU-only mode")
            except Exception as e:
                print(f"⚠️  Failed to get GPU count: {e}, using default GPU 0")
                gpu_ids = [0]
        else:
            gpu_ids = [int(x.strip()) for x in gpu_config.split(",")]
            print(f"🖥️  Using configured GPUs: {gpu_ids}")
        
        # Get command runner
        command_runner = self.target_config.get("command_runner", "uv run")
        
        # Create session name - extract the actual sweep ID from the full path
        # From "yangbn/JasmineTool/ciwmshft" extract "ciwmshft"
        sweep_id_parts = sweep_id.split('/')
        short_sweep_id = sweep_id_parts[-1] if sweep_id_parts else sweep_id
        current_time = time.strftime("%m%d%H%M")
        session_name = f"{short_sweep_id}_{current_time}"
        
        if self.verbose:
            print(f"   Session name: {session_name}")
            print(f"   GPUs: {gpu_ids}")
            print(f"   Processes per GPU: {num_processes}")
            print(f"   Command runner: {command_runner}")
        
        # Create new tmux session
        tmux_cmd = ["tmux", "new-session", "-d", "-s", session_name]
        result = subprocess.run(tmux_cmd, capture_output=True)
        
        if result.returncode != 0:
            print(f"❌ Failed to create tmux session: {result.stderr.decode()}")
            return False
        
        first_pane = True
        
        # Check if nvidia-smi exists locally
        has_nvidia_smi = False
        try:
            result = subprocess.run(["nvidia-smi", "--version"], capture_output=True)
            has_nvidia_smi = (result.returncode == 0)
        except FileNotFoundError:
            has_nvidia_smi = False
        
        # Create panes and start processes
        for gpu_id in gpu_ids:
            for i in range(num_processes):
                if not first_pane:
                    # Split window to create new pane
                    split_cmd = ["tmux", "split-window", "-t", session_name]
                    subprocess.run(split_cmd)
                    
                    # Arrange panes in tiled layout
                    layout_cmd = ["tmux", "select-layout", "-t", session_name, "tiled"]
                    subprocess.run(layout_cmd)
                
                # Build command to run in pane
                wandb_cmd = f"wandb agent {sweep_id}"  # Use full sweep_id for the command
                
                # Only set CUDA_VISIBLE_DEVICES if nvidia-smi exists
                if has_nvidia_smi:
                    full_command = f"export WANDB_API_KEY={wandb_key} && CUDA_VISIBLE_DEVICES={gpu_id} {command_runner} {wandb_cmd}"
                else:
                    full_command = f"export WANDB_API_KEY={wandb_key} && {command_runner} {wandb_cmd}"
                
                # Send command to pane
                send_cmd = ["tmux", "send-keys", "-t", session_name, full_command, "C-m"]
                subprocess.run(send_cmd)
                
                if self.verbose:
                    if has_nvidia_smi:
                        print(f"   ✅ Started process {i+1} on GPU {gpu_id}")
                    else:
                        print(f"   ✅ Started process {i+1} (CPU-only mode)")
                
                first_pane = False
        
        print(f"🚀 All processes started in tmux session: {session_name}")
        print(f"   View session: tmux attach-session -t {session_name}")
        print(f"   Kill session: tmux kill-session -t {session_name}")
        
        return True
    
    def start(self) -> bool:
        """Start wandb agents for the target configuration"""
        if self.verbose:
            print(f"🎯 Starting wandb agents for target: {self.target}")
        
        # Load and validate configuration
        if not self.load_config():
            return False
        
        if not self.validate_target():
            return False
        
        # Change to work directory
        try:
            if not self.work_dir:
                print("❌ Work directory not set")
                return False
                
            os.chdir(self.work_dir)
            if self.verbose:
                print(f"📂 Changed to work directory: {self.work_dir}")
            
            # Get wandb key
            wandb_key = self.get_wandb_key()
            if not wandb_key:
                print("❌ Failed to get WANDB API key")
                return False
            
            # Get sweep ID from sweep file
            sweep_id = self.extract_sweep_id_from_file()
            if not sweep_id:
                print("❌ Failed to extract sweep ID from file")
                return False
            
            print(f"✅ Using sweep ID: {sweep_id}")
            
            # Get temporary configuration with user input
            temp_config = self.get_temporary_config()
            
            # Create tmux session
            print("\n🚀 Creating tmux session...")
            success = self.create_tmux_session(
                temp_config["gpu_config"],
                temp_config["num_processes"],
                wandb_key,
                sweep_id
            )
            
            return success
            
        except Exception as e:
            print(f"❌ Error during start operation: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False
        
        finally:
            # Restore original directory
            os.chdir(self.original_cwd)


def start_wandb_agents(config_path: str, target: str, verbose: bool = False) -> bool:
    """
    Start wandb agents for a given target configuration.
    This is the main entry point called by the CLI.
    """
    try:
        # Load configuration
        config = ConfigManager.load_config(config_path)
        if not config:
            print("❌ Failed to load configuration")
            return False
        
        # Get target configuration
        if target not in config:
            print(f"❌ Target '{target}' not found in configuration")
            return False
        
        target_config = config[target]
        
        # Check if this is a remote target (has ssh_host)
        ssh_host = target_config.get('ssh_host')
        
        if ssh_host:
            # Remote execution
            if verbose:
                print(f"🌐 Executing start command on remote host: {ssh_host}")
            
            return start_wandb_agents_remote(config_path, config, target, target_config, verbose)
        else:
            # Local execution
            if verbose:
                print("🏠 Executing start command locally")
            
            manager = StartManager(config_path, target, verbose)
            return manager.start()
    
    except Exception as e:
        print(f"❌ Error in start_wandb_agents: {e}")
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



def create_tmux_session_remote(remote_executor: RemoteTargetExecutor, sweep_id: str, gpu_config: str, num_processes: int, wandb_key: str, command_runner: str, verbose: bool = False) -> bool:
    """Create tmux session with wandb agents on remote host"""
    print("🚀 Creating tmux session...")
    
    # Get the correct uv command
    uv_cmd = get_uv_command(remote_executor)
    
    # Replace uv in command_runner if needed
    if command_runner.startswith("uv run"):
        command_runner = command_runner.replace("uv run", f"{uv_cmd} run")
    
    # Step 1: Check if nvidia-smi exists and get GPU configuration
    print("📝 Checking GPU configuration...")
    if gpu_config == "0":
        # Check if nvidia-smi exists
        result = remote_executor.ssh.execute_command("command -v nvidia-smi", capture_output=True)
        if result.returncode == 0:
            print("🖥️  nvidia-smi found, detecting GPUs...")
            # Get GPU count
            result = remote_executor.ssh.execute_command("nvidia-smi --query-gpu=count --format=csv,noheader | wc -l", capture_output=True)
            if result.returncode == 0:
                try:
                    num_gpus = int(result.stdout.strip())
                    if num_gpus > 0:
                        gpu_ids = ",".join([str(i) for i in range(num_gpus)])
                        print(f"🖥️  Detected {num_gpus} GPU(s): {gpu_ids}")
                    else:
                        gpu_ids = "0"
                        print("⚠️  No GPUs detected, using default: 0")
                except ValueError:
                    gpu_ids = "0"
                    print("⚠️  Failed to parse GPU count, using default: 0")
            else:
                gpu_ids = "0"
                print("⚠️  nvidia-smi failed, using default: 0")
        else:
            gpu_ids = "0"
            print("⚠️  nvidia-smi not found, using CPU-only mode: 0")
    else:
        gpu_ids = gpu_config
        print(f"🖥️  Using configured GPUs: {gpu_ids}")
    
    # Step 2: Create session name
    sweep_id_short = sweep_id.split('/')[-1] if '/' in sweep_id else sweep_id
    import time
    current_time = time.strftime("%m%d%H%M")
    session_name = f"{sweep_id_short}_{current_time}"
    print(f"📝 Session name: {session_name}")
    
    # Step 3: Create tmux session
    print("🔧 Creating tmux session...")
    result = remote_executor.ssh.execute_command(f"tmux new-session -d -s {session_name}", capture_output=True)
    if result.returncode != 0:
        print("✗ Failed to create tmux session")
        return False
    
    # Step 4: Add processes to tmux session
    print("🔧 Adding processes to tmux session...")
    gpu_list = [g.strip() for g in gpu_ids.split(",")]
    first_pane = True
    
    # Check if we have nvidia-smi for environment variable setting
    has_nvidia_result = remote_executor.ssh.execute_command("command -v nvidia-smi", capture_output=True)
    has_nvidia = (has_nvidia_result.returncode == 0)
    
    for gpu_id in gpu_list:
        for i in range(num_processes):
            if not first_pane:
                # Split window
                result = remote_executor.ssh.execute_command(f"tmux split-window -t {session_name}", capture_output=True)
                if result.returncode != 0:
                    print(f"⚠️  Failed to split window, continuing...")
                
                # Arrange layout
                result = remote_executor.ssh.execute_command(f"tmux select-layout -t {session_name} tiled", capture_output=True)
            
            # Build command
            wandb_cmd = f"wandb agent {sweep_id}"
            if has_nvidia:
                full_cmd = f"export WANDB_API_KEY={wandb_key} && CUDA_VISIBLE_DEVICES={gpu_id} {command_runner} {wandb_cmd}"
            else:
                full_cmd = f"export WANDB_API_KEY={wandb_key} && {command_runner} {wandb_cmd}"
            
            # Send command to pane
            result = remote_executor.ssh.execute_command(f'tmux send-keys -t {session_name} "{full_cmd}" C-m', capture_output=True)
            if result.returncode == 0:
                if has_nvidia:
                    print(f"✅ Started process {i+1} on GPU {gpu_id}")
                else:
                    print(f"✅ Started process {i+1} (CPU mode)")
            else:
                print(f"⚠️  Failed to start process {i+1}")
            
            first_pane = False
    
    print("🎉 All processes started successfully!")
    print(f"🚀 Tmux session created: {session_name}")
    print(f"   View session: tmux attach-session -t {session_name}")
    print(f"   Kill session: tmux kill-session -t {session_name}")
    
    return True


def get_wandb_key_for_remote(config: Dict[str, Any], target_config: Dict[str, Any], verbose: bool = False) -> str:
    """Get wandb key from local config for remote execution"""
    print("🔑 Getting WANDB API key from local config...")
    
    # First try target specific wandb_key from local config
    if "wandb_key" in target_config:
        if verbose:
            print("✅ Using wandb_key from local target configuration")
        return target_config["wandb_key"]
    
    # Then try global wandb_key from local config  
    if "wandb_key" in config:
        if verbose:
            print("✅ Using wandb_key from local global configuration")
        return config["wandb_key"]
    
    # Finally try local environment variable
    wandb_key = os.environ.get("WANDB_API_KEY", "")
    if wandb_key:
        if verbose:
            print("✅ Using WANDB_API_KEY from local environment variable")
        return wandb_key
    
    print("❌ WANDB_API_KEY not found in local config or environment")
    return ""


def start_wandb_agents_remote(config_path: str, config: Dict[str, Any], target: str, target_config: Dict[str, Any], verbose: bool = False) -> bool:
    """Start wandb agents on remote host"""
    try:
        # Create remote executor
        remote_executor = RemoteTargetExecutor(target_config, verbose)
        
        # Validate connection
        if not remote_executor.validate_connection():
            return False
        
        # Get configuration values
        config_dir = Path(config_path).parent.resolve()
        sweep_file_path_str = config.get('sweep_file', 'sweep_config.yaml')
        
        # Handle sweep file path
        if Path(sweep_file_path_str).is_absolute():
            sweep_file_path = Path(sweep_file_path_str)
        elif '/' in sweep_file_path_str or '\\' in sweep_file_path_str:
            if not (sweep_file_path_str.startswith('.jasminetool/') or sweep_file_path_str.startswith('./jasminetool/')):
                print(f"❌ Relative paths are not allowed for sweep_file: {sweep_file_path_str}")
                return False
            sweep_file_path_str = sweep_file_path_str.replace('.jasminetool/', '').replace('./jasminetool/', '')
            sweep_file_path = config_dir / sweep_file_path_str
        else:
            sweep_file_path = config_dir / sweep_file_path_str
        
        # Read sweep file locally
        if not sweep_file_path.exists():
            print(f"❌ Sweep file not found: {sweep_file_path}")
            return False
        
        # Extract sweep ID from local file
        with open(sweep_file_path, 'r') as f:
            content = f.read()
        
        sweep_id = None
        lines = content.strip().split('\n')
        for line in lines:
            if 'wandb agent' in line and 'Run sweep agent with:' in line:
                parts = line.split('wandb agent')
                if len(parts) > 1:
                    sweep_id = parts[-1].strip()
                    break
        
        if not sweep_id:
            print(f"❌ Could not find sweep ID in file: {sweep_file_path}")
            return False
        
        print(f"✅ Using sweep ID: {sweep_id}")
        
        # Get configuration values
        default_gpu_config = target_config.get("gpu_config", "0,1,2,3")
        default_num_processes = target_config.get("num_processes", 1)
        command_runner = target_config.get("command_runner", "uv run")

        # Ask user if they want to change the gpu config and num_processes temporarily
        # Wait 3s for user input
        print(f"📋 Current configuration:")
        print(f"   gpu_config: {default_gpu_config}")
        print(f"   num_processes: {default_num_processes}")
        print()
        
        # Create a temporary StartManager instance to reuse the input logic
        temp_manager = StartManager(config_path, target, verbose)
        temp_manager.config = config
        temp_manager.target_config = target_config
        
        # Get user input with timeout
        gpu_input = temp_manager.get_user_input_with_timeout(
            f"Enter GPU configuration (default: {default_gpu_config})"
        )
        
        if gpu_input:
            gpu_config = gpu_input
            print(f"✅ Using GPU configuration: {gpu_config}")
        else:
            gpu_config = default_gpu_config
            print(f"⏰ Timeout - using default GPU configuration: {gpu_config}")
        
        # Get number of processes
        num_input = temp_manager.get_user_input_with_timeout(
            f"Enter number of processes per GPU (default: {default_num_processes})"
        )
        
        if num_input:
            try:
                num_processes = int(num_input)
                print(f"✅ Using number of processes: {num_processes}")
            except ValueError:
                num_processes = default_num_processes
                print(f"❌ Invalid number - using default: {num_processes}")
        else:
            num_processes = default_num_processes
            print(f"⏰ Timeout - using default number of processes: {num_processes}")
        
        print()  # Add blank line for better readability
        
        # Get wandb key from local config
        wandb_key = get_wandb_key_for_remote(config, target_config, verbose)
        if not wandb_key:
            print("❌ WANDB_API_KEY not found in local config or environment")
            print("   Please add wandb_key to your local configuration:")
            print("   - Add to target config: wandb_key: your_key_here")
            print("   - Add to global config: wandb_key: your_key_here")
            print("   - Set environment variable: export WANDB_API_KEY=your_key_here")
            return False
        
        print(f"🚀 Starting remote wandb agents...")
        print(f"🖥️  GPU config: {gpu_config}")
        print(f"⚙️  Processes per GPU: {num_processes}")
        print(f"🔑 WANDB key: {'***' + wandb_key[-4:] if len(wandb_key) > 4 else '***'}")
        print(f"▶️  Command runner: {command_runner}")
        print("=" * 60)
        
        # Create tmux session with wandb agents
        if not create_tmux_session_remote(remote_executor, sweep_id, gpu_config, num_processes, wandb_key, command_runner, verbose):
            return False
        
        print("=" * 60)
        print("🎉 Remote wandb agents started successfully!")
        print(f"🔍 To view: ssh {target_config.get('ssh_host')} 'tmux list-sessions'")
        print(f"🔗 To attach: ssh {target_config.get('ssh_host')} 'tmux attach-session -t <session_name>'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error starting wandb agents remotely: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


 