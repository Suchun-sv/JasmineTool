#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Execution Modes

Different execution modes for the JasmineTool system.
"""

import os
import subprocess
import yaml
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod

from .utils import TmuxManager


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
        
        print(f"Executing SSH command: {ssh_command}")
        
        # Execute SSH command
        result = subprocess.run(ssh_command, shell=True)
        return result.returncode == 0
    
    def _execute_rsync(self, sync_source: str, sync_target: str, sync_exclude: List[str]) -> bool:
        """Execute rsync command"""
        exclude_args = []
        for exclude in sync_exclude:
            exclude_args.extend(['--exclude', exclude])
        
        rsync_cmd = ['rsync', '-avz', '--delete'] + exclude_args + [sync_source, sync_target]
        
        print(f"Executing rsync: {' '.join(rsync_cmd)}")
        result = subprocess.run(rsync_cmd)
        return result.returncode == 0


class SlurmMode(ExecutionMode):
    """SLURM execution mode"""
    
    def execute(self, config: Dict[str, Any], command: str, **kwargs) -> bool:
        """Execute task via SLURM"""
        slurm_config = config.get('slurm_config', {})
        
        # Build SLURM script
        slurm_script = self._build_slurm_script(slurm_config, command)
        
        # Write script to temporary file
        script_path = '/tmp/slurm_job.sh'
        with open(script_path, 'w') as f:
            f.write(slurm_script)
        
        # Submit job
        sbatch_cmd = ['sbatch', script_path]
        print(f"Submitting SLURM job: {' '.join(sbatch_cmd)}")
        
        result = subprocess.run(sbatch_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Job submitted successfully: {result.stdout.strip()}")
            return True
        else:
            print(f"Job submission failed: {result.stderr.strip()}")
            return False
    
    def _build_slurm_script(self, slurm_config: Dict[str, Any], command: str) -> str:
        """Build SLURM script content"""
        script_lines = ['#!/bin/bash']
        
        # Add SLURM directives
        for key, value in slurm_config.items():
            script_lines.append(f'#SBATCH --{key}={value}')
        
        # Add command
        script_lines.append('')
        script_lines.append(command)
        
        return '\n'.join(script_lines)


class RemoteGpuMode(ExecutionMode):
    """Remote GPU execution mode with dynamic SSH configuration"""
    
    def execute(self, config: Dict[str, Any], command: str, **kwargs) -> bool:
        """Execute task on remote GPU server"""
        current_branch = kwargs.get('current_branch', 'main')
        
        # Get available servers
        servers = config.get('servers', [])
        if not servers:
            print("No servers configured for remote_gpu mode")
            return False
        
        # Try each server until one works
        for server in servers:
            if self._try_execute_on_server(server, command, current_branch):
                return True
        
        print("Failed to execute on any server")
        return False
    
    def _try_execute_on_server(self, server_config: Dict[str, Any], command: str, current_branch: str) -> bool:
        """Try to execute on a specific server"""
        ssh_host = server_config['ssh_host']
        work_dir = server_config['work_dir']
        gpu_config = server_config['gpu_config']
        num_processes = server_config['num_processes']
        
        # Test SSH connection
        test_cmd = f'ssh -o ConnectTimeout=5 {ssh_host} echo "Connection test"'
        test_result = subprocess.run(test_cmd, shell=True, capture_output=True)
        
        if test_result.returncode != 0:
            print(f"Cannot connect to {ssh_host}, trying next server")
            return False
        
        print(f"Successfully connected to {ssh_host}")
        
        # Build remote commands
        remote_commands = []
        remote_commands.append(f'cd "{work_dir}"')
        remote_commands.append('echo "Now in remote directory: $(pwd)"')
        
        # Git operations
        if server_config.get('sync_method') == 'git' and 'git_operations' in server_config:
            for git_op in server_config['git_operations']:
                git_cmd = git_op.format(branch=current_branch)
                remote_commands.append(git_cmd)
        
        # Create tmux session remotely
        tmux_script = TmuxManager.create_tmux_session(gpu_config, num_processes, command, remote=True)
        remote_commands.append(tmux_script)
        
        # Build SSH command
        ssh_script = '\n'.join(remote_commands)
        ssh_command = f'ssh {ssh_host} << EOF\n{ssh_script}\nexit\nEOF'
        
        print(f"Executing on {ssh_host}")
        
        # Execute SSH command
        result = subprocess.run(ssh_command, shell=True)
        return result.returncode == 0 