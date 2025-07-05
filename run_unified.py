#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified Task Runner

A configuration-driven task execution system that supports multiple execution modes:
- local: Execute tasks locally
- remote: Execute tasks on remote servers via SSH
- slurm: Submit tasks to SLURM batch system
- remote_gpu: Execute tasks on remote GPU servers with dynamic SSH configuration
"""

import sys
import os
import subprocess
import yaml
import argparse
import signal
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod


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
                    num_gpus = len(result.stdout.strip().split('\n'))
                    return [str(i) for i in range(num_gpus)]
            except:
                pass
            return ["0"]
        
        # Parse comma-separated GPU IDs
        return [gpu.strip() for gpu in gpu_config.split(',')]
    
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
                
                if gpu_id:
                    cuda_env = f"CUDA_VISIBLE_DEVICES={gpu_id}"
                    full_command = f"{env_setup} && {cuda_env} {command}"
                else:
                    full_command = f"{env_setup} && {command}"
                
                tmux_commands.append(f'tmux send-keys -t "{session_name}" "{full_command}" C-m')
                print(f"Started process {i} on GPU {gpu_id} in tmux session {session_name}")
                
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


class ExecutionMode(ABC):
    """Abstract base class for different execution modes"""
    
    @abstractmethod
    def execute(self, config: Dict[str, Any], command: str, **kwargs) -> bool:
        """Execute the task with given configuration and command"""
        pass


class LocalMode(ExecutionMode):
    """Local execution mode"""
    
    def execute(self, config: Dict[str, Any], command: str, **kwargs) -> bool:
        """Execute task locally"""
        gpu_config = config['gpu_config']
        num_processes = config['num_processes']
        
        print(f"Executing in local mode")
        session_name = TmuxManager.create_tmux_session(gpu_config, num_processes, command, remote=False)
        
        return bool(session_name)


class RemoteMode(ExecutionMode):
    """Remote execution mode"""
    
    def execute(self, config: Dict[str, Any], command: str, **kwargs) -> bool:
        """Execute task on remote server"""
        current_branch = kwargs.get('current_branch', 'main')
        
        ssh_host = config['ssh_host']
        work_dir = config['work_dir']
        gpu_config = config['gpu_config']
        num_processes = config['num_processes']
        
        # Handle synchronization
        if config.get('sync_method') == 'rsync':
            if not self._execute_rsync(config['sync_source'], config['sync_target'], 
                                     config.get('sync_exclude', [])):
                return False
        
        # Build remote commands
        remote_commands = []
        remote_commands.append(f'cd "{work_dir}"')
        remote_commands.append('echo "Now in remote directory: $(pwd)"')
        
        # Git operations
        if config.get('sync_method') == 'git' and 'git_operations' in config:
            for git_op in config['git_operations']:
                git_cmd = git_op.format(branch=current_branch)
                remote_commands.append(git_cmd)
        
        # Create tmux session remotely
        tmux_script = TmuxManager.create_tmux_session(gpu_config, num_processes, command, remote=True)
        remote_commands.append(tmux_script)
        
        # Build SSH command
        ssh_script = '\n'.join(remote_commands)
        ssh_command = f'ssh {ssh_host} << EOF\n{ssh_script}\nexit\nEOF'
        
        print(f"Executing remote commands on {ssh_host}")
        result = subprocess.run(ssh_command, shell=True)
        return result.returncode == 0
    
    def _execute_rsync(self, sync_source: str, sync_target: str, sync_exclude: List[str]) -> bool:
        """Execute rsync synchronization"""
        exclude_args = []
        for exclude in sync_exclude:
            exclude_args.extend(['--exclude', exclude])
        
        cmd = ['rsync', '-avP', sync_source, sync_target] + exclude_args
        print(f"Executing: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        return result.returncode == 0


class SlurmMode(ExecutionMode):
    """SLURM batch system execution mode"""
    
    def execute(self, config: Dict[str, Any], command: str, **kwargs) -> bool:
        """Submit task to SLURM batch system"""
        ssh_host = config['ssh_host']
        work_dir = config['work_dir']
        num_processes = config['num_processes']
        partition = config['slurm_partition']
        script = config['slurm_script']
        env = config['slurm_env']
        
        # Replace variables in work directory
        current_dir = os.getcwd()
        home_dir = os.path.expanduser('~')
        relative_dir = current_dir.replace(home_dir, '')
        work_dir = work_dir.format(current_dir=relative_dir)
        
        # Build remote commands
        remote_commands = []
        remote_commands.append(f'cd "{work_dir}"')
        
        # Submit multiple jobs
        for i in range(num_processes):
            sbatch_cmd = f'sbatch -p {partition} {script} {env} "{command}"'
            remote_commands.append(f'echo "Running command: {sbatch_cmd}"')
            remote_commands.append(sbatch_cmd)
        
        # Build SSH command
        ssh_script = '\n'.join(remote_commands)
        ssh_command = f'ssh {ssh_host} << EOF\n{ssh_script}\nexit\nEOF'
        
        print(f"Executing SLURM commands on {ssh_host}")
        result = subprocess.run(ssh_command, shell=True)
        return result.returncode == 0


class RemoteGpuMode(ExecutionMode):
    """Remote GPU execution mode with dynamic SSH configuration"""
    
    def execute(self, config: Dict[str, Any], command: str, **kwargs) -> bool:
        """Execute task on remote GPU server"""
        ssh_host = config['ssh_host']
        work_dir = config['work_dir']
        gpu_config = config['gpu_config']
        num_processes = config['num_processes']
        
        # Get SSH configuration
        ssh_config_cmd = f'ssh {ssh_host} \'cat {config["ssh_config_source"]}\''
        result = subprocess.run(ssh_config_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0 or not result.stdout.strip():
            print(f"Failed to get SSH config from {ssh_host}")
            return False
        
        # Parse SSH configuration
        ssh_config = result.stdout
        hostname = user = port = None
        
        for line in ssh_config.split('\n'):
            if 'HostName' in line:
                hostname = line.split()[1]
            elif 'User' in line:
                user = line.split()[1]
            elif 'Port' in line:
                port = line.split()[1]
        
        if not all([hostname, user, port]):
            print("Failed to parse SSH config")
            return False
        
        print(f"Got SSH config: ssh {user}@{hostname} -p {port}")
        
        # Replace variables in work directory
        current_dir = os.getcwd()
        home_dir = os.path.expanduser('~')
        relative_dir = current_dir.replace(home_dir, '')
        work_dir = work_dir.format(current_dir=relative_dir)
        
        # Build remote commands
        remote_commands = []
        remote_commands.append(f'cd "{work_dir}"')
        remote_commands.append('echo "Now in remote directory: $(pwd)"')
        
        # Create tmux session remotely
        tmux_script = TmuxManager.create_tmux_session(gpu_config, num_processes, command, remote=True)
        remote_commands.append(tmux_script)
        
        # Build SSH command
        ssh_script = '\n'.join(remote_commands)
        proxy_option = ""
        if 'ssh_proxy' in config:
            proxy_option = f'-o ProxyCommand="ssh -W %h:%p {config["ssh_proxy"]}"'
        
        ssh_command = f'ssh {user}@{hostname} -p {port} {proxy_option} -o StrictHostKeyChecking=no << EOF\n{ssh_script}\nexit\nEOF'
        
        print(f"Executing remote GPU commands on {hostname}")
        result = subprocess.run(ssh_command, shell=True)
        return result.returncode == 0


class ConfigManager:
    """Configuration file manager"""
    
    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        """Load YAML configuration file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")
    
    @staticmethod
    def save_config(config: Dict[str, Any], config_path: str) -> bool:
        """Save configuration to YAML file"""
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True)
            return True
        except Exception as e:
            print(f"Failed to save configuration: {e}")
            return False


class GitManager:
    """Git operations manager"""
    
    @staticmethod
    def check_git_status(git_dir: str) -> bool:
        """Check if git repository is clean"""
        try:
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  cwd=git_dir, capture_output=True, text=True)
            if result.stdout.strip():
                print("The current directory is not clean. Please commit or stash your changes.")
                return False
            return True
        except Exception as e:
            print(f"Git check failed: {e}")
            return False
    
    @staticmethod
    def get_current_branch(git_dir: str) -> str:
        """Get current git branch"""
        try:
            result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                                  cwd=git_dir, capture_output=True, text=True)
            return result.stdout.strip()
        except Exception:
            return "main"


class CommandExtractor:
    """Command extraction from sweep files"""
    
    @staticmethod
    def get_sweep_command(sweep_file: str, pattern: str) -> str:
        """Extract command from sweep file"""
        try:
            with open(sweep_file, 'r') as f:
                content = f.read()
                for line in content.split('\n'):
                    if 'wandb agent' in line:
                        # Simple text processing replacement
                        return line.replace('wandb: Run sweep agent with: ', '')
            return ""
        except FileNotFoundError:
            print(f"Warning: {sweep_file} not found")
            return ""


class PreCommandExecutor:
    """Pre-command execution manager"""
    
    @staticmethod
    def execute_pre_commands(pre_commands: List[Dict[str, Any]]) -> bool:
        """Execute pre-processing commands"""
        for pre_cmd in pre_commands:
            host = pre_cmd['host']
            commands = pre_cmd['commands']
            
            ssh_script = ' && '.join(commands)
            ssh_command = f'ssh {host} << EOF\n{ssh_script}\nexit\nEOF'
            
            print(f"Executing pre-commands on {host}")
            result = subprocess.run(ssh_command, shell=True)
            if result.returncode != 0:
                print(f"Pre-command failed on {host}")
                return False
        return True


class UnifiedTaskRunner:
    """Main task runner class"""
    
    def __init__(self, config_path: str = './tools/agent_config.yaml'):
        self.config_path = config_path
        self.config = None
        self.config_modified = False
        self.execution_modes = {
            'local': LocalMode(),
            'remote': RemoteMode(),
            'slurm': SlurmMode(),
            'remote_gpu': RemoteGpuMode()
        }
        self.timeout_input = TimeoutInput(timeout=3)
    
    def load_configuration(self) -> bool:
        """Load configuration from file"""
        try:
            self.config = ConfigManager.load_config(self.config_path)
            return True
        except Exception as e:
            print(f"Failed to load configuration: {e}")
            return False
    
    def save_configuration(self) -> bool:
        """Save configuration to file"""
        if self.config_modified:
            print("Configuration has been modified. Saving changes...")
            if ConfigManager.save_config(self.config, self.config_path):
                print(f"Configuration saved to {self.config_path}")
                return True
            else:
                print("Failed to save configuration")
                return False
        return True
    
    def validate_target(self, target: str) -> bool:
        """Validate if target exists in configuration"""
        if target not in self.config['targets']:
            print(f"Unknown target: {target}")
            print(f"Available targets: {list(self.config['targets'].keys())}")
            return False
        return True
    
    def get_sweep_command(self) -> Optional[str]:
        """Get sweep command from configuration"""
        global_config = self.config['global']
        command = CommandExtractor.get_sweep_command(
            global_config['sweep_file'], 
            global_config['command_extract_pattern']
        )
        if not command:
            print("Failed to get command from sweep file")
            return None
        return command
    
    def confirm_execution(self, command: str) -> bool:
        """Confirm execution with user"""
        print(f"Running command: {command}")
        response = input("Do you want to run the command above? (y/n) ")
        return response.lower() in ['y', 'yes']
    
    def interactive_config_update(self, target_config: Dict[str, Any]) -> None:
        """Interactive configuration update for GPU config and num_processes"""
        print(f"\n--- Interactive Configuration ---")
        print(f"Target: {target_config['name']}")
        
        # Get current values
        current_gpu_config = target_config.get('gpu_config', '0')
        current_num_processes = target_config.get('num_processes', 1)
        
        # Ask for GPU config
        new_gpu_config = self.timeout_input.get_input(
            f"GPU config", 
            str(current_gpu_config)
        )
        
        # Ask for num_processes
        new_num_processes = self.timeout_input.get_input(
            f"Number of processes", 
            str(current_num_processes)
        )
        
        # Update configuration if changed
        if new_gpu_config != str(current_gpu_config):
            target_config['gpu_config'] = new_gpu_config
            self.config_modified = True
            print(f"GPU config updated: {current_gpu_config} -> {new_gpu_config}")
        
        if new_num_processes != str(current_num_processes):
            try:
                target_config['num_processes'] = int(new_num_processes)
                self.config_modified = True
                print(f"Number of processes updated: {current_num_processes} -> {new_num_processes}")
            except ValueError:
                print(f"Invalid number of processes: {new_num_processes}, keeping current value: {current_num_processes}")
        
        print("--- Configuration Complete ---\n")
    
    def prepare_git_environment(self, target_config: Dict[str, Any]) -> Optional[str]:
        """Prepare git environment and return current branch"""
        current_branch = "main"
        if target_config.get('check_git'):
            git_dir = os.path.join(os.getcwd(), self.config['global']['local_git_dir'])
            if not GitManager.check_git_status(git_dir):
                return None
            current_branch = GitManager.get_current_branch(git_dir)
            print(f"Current git branch: {current_branch}")
        return current_branch
    
    def execute_pre_commands(self, target_config: Dict[str, Any]) -> bool:
        """Execute pre-commands if configured"""
        if 'pre_commands' in target_config:
            return PreCommandExecutor.execute_pre_commands(target_config['pre_commands'])
        return True
    
    def execute_target(self, target: str, skip_confirmation: bool = False, skip_interactive: bool = False) -> bool:
        """Execute target with given configuration"""
        if not self.load_configuration():
            return False
        
        if not self.validate_target(target):
            return False
        
        target_config = self.config['targets'][target]
        global_config = self.config['global']
        
        # Interactive configuration update
        if not skip_interactive:
            self.interactive_config_update(target_config)
        
        # Get command
        command = self.get_sweep_command()
        if not command:
            return False
        
        # Confirm execution
        if not skip_confirmation and global_config['confirm_before_run']:
            if not self.confirm_execution(command):
                print("Execution cancelled")
                return True  # Not an error, just cancelled
        
        # Save configuration if modified
        if not self.save_configuration():
            return False
        
        # Prepare git environment
        current_branch = self.prepare_git_environment(target_config)
        if current_branch is None:
            return False
        
        # Execute pre-commands
        if not self.execute_pre_commands(target_config):
            return False
        
        # Execute based on mode
        mode = target_config['mode']
        if mode not in self.execution_modes:
            print(f"Unknown execution mode: {mode}")
            return False
        
        execution_mode = self.execution_modes[mode]
        success = execution_mode.execute(target_config, command, current_branch=current_branch)
        
        if success:
            print("Execution completed successfully")
        else:
            print("Execution failed")
        
        return success


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Unified Task Execution System')
    parser.add_argument('target', help='Target name to execute')
    parser.add_argument('--config', default='./tools/agent_config.yaml', help='Configuration file path')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--no-interactive', action='store_true', help='Skip interactive configuration')
    
    args = parser.parse_args()
    
    # Create and run task runner
    runner = UnifiedTaskRunner(args.config)
    success = runner.execute_target(args.target, args.yes, args.no_interactive)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main()) 