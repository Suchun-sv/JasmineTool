#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SSH Executor Module

This module provides functionality to execute commands on remote hosts via SSH.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import shlex


class SSHExecutor:
    """Execute commands on remote hosts via SSH"""
    
    def __init__(self, ssh_host: str, ssh_port: int, work_dir: str, verbose: bool = False):
        """Initialize SSH executor"""
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.work_dir = work_dir
        self.verbose = verbose
    
    def test_connection(self) -> bool:
        """Test SSH connection to the remote host"""
        try:
            cmd = f"ssh -p {self.ssh_port} -o ConnectTimeout=5 -o BatchMode=yes {self.ssh_host} echo 'Connection test'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                if self.verbose:
                    print(f"✅ SSH connection to {self.ssh_host} successful")
                return True
            else:
                print(f"❌ SSH connection to {self.ssh_host} failed")
                if self.verbose:
                    print(f"   Error: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error testing SSH connection: {e}")
            print(f"You can try to connect to {self.ssh_host} manually to check if the SSH connection is successful with the following command:")
            print(f"ssh -p {self.ssh_port} {self.ssh_host}")
            print(f"{cmd}")
            return False
    
    def execute_command(self, command: str, capture_output: bool = True, no_work_dir: bool = False, stream_output: bool = False, force_pty: bool = False) -> subprocess.CompletedProcess:
        """Execute a single command on the remote host"""
        # Escape single quotes in command to prevent shell injection
        escaped_command = command.replace("'", "'\"'\"'")
        
        # Build the SSH command
        ssh_base = f"ssh -p {self.ssh_port}"
        
        # Add PTY allocation for interactive/streaming commands
        if stream_output or force_pty:
            ssh_base += " -t"
        
        if no_work_dir:
            ssh_cmd = f"{ssh_base} {self.ssh_host} '{escaped_command}'"
        else:
            ssh_cmd = f"{ssh_base} {self.ssh_host} 'cd {self.work_dir} && {escaped_command}'"
        
        if self.verbose:
            print(f"🔧 Executing on {self.ssh_host}: {command}")
        
        # Execute the command with streaming output if requested
        if stream_output:
            return self._execute_with_stream(ssh_cmd)
        elif capture_output:
            result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
            if self.verbose:
                print(f"✅ Command completed with return code: {result.returncode}")
            if result.returncode != 0:
                print(f"❌ Command failed: {result.stderr}")
            return result
        else:
            result = subprocess.run(ssh_cmd, shell=True, text=True)
            if self.verbose:
                print(f"✅ Command completed with return code: {result.returncode}")
            return result
    
    def _execute_with_stream(self, ssh_cmd: str) -> subprocess.CompletedProcess:
        """Execute command with real-time output streaming"""
        import sys
        import select
        
        # Use Popen for streaming output
        process = subprocess.Popen(
            ssh_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,  # Keep stderr separate to handle progress bars
            text=True,
            bufsize=0,  # Unbuffered for real-time output
            universal_newlines=True
        )
        
        output_lines = []
        error_lines = []
        
        # Read output in real-time
        try:
            while True:
                # Check if process has terminated
                if process.poll() is not None:
                    break
                
                # Use select to check for available input (Unix only)
                try:
                    import select
                    ready, _, _ = select.select([process.stdout, process.stderr], [], [], 0.1)
                    
                    for stream in ready:
                        if stream is process.stdout:
                            line = stream.readline()
                            if line:
                                print(line, end='', flush=True)
                                output_lines.append(line)
                        elif stream is process.stderr:
                            line = stream.readline()
                            if line:
                                # Print stderr in real-time (this includes progress bars)
                                print(line, end='', flush=True)
                                error_lines.append(line)
                except (ImportError, OSError):
                    # Fallback for Windows or when select is not available
                    if process.stdout:
                        line = process.stdout.readline()
                        if line:
                            print(line, end='', flush=True)
                            output_lines.append(line)
                    if process.stderr:
                        line = process.stderr.readline()
                        if line:
                            print(line, end='', flush=True)
                            error_lines.append(line)
                            
        except KeyboardInterrupt:
            print("\n⚠️  Command interrupted by user")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            return subprocess.CompletedProcess(
                args=ssh_cmd,
                returncode=-1,
                stdout=''.join(output_lines),
                stderr="Command interrupted by user"
            )
        
        # Read any remaining output
        remaining_stdout = process.stdout.read() if process.stdout else ""
        remaining_stderr = process.stderr.read() if process.stderr else ""
        
        if remaining_stdout:
            print(remaining_stdout, end='', flush=True)
            output_lines.append(remaining_stdout)
        if remaining_stderr:
            print(remaining_stderr, end='', flush=True)
            error_lines.append(remaining_stderr)
        
        # Wait for process to complete
        return_code = process.wait()
        
        if self.verbose:
            print(f"\n✅ Command completed with return code: {return_code}")
        
        # Create a CompletedProcess-like object
        return subprocess.CompletedProcess(
            args=ssh_cmd,
            returncode=return_code,
            stdout=''.join(output_lines),
            stderr=''.join(error_lines)
        )
    
    def execute_commands(self, commands: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """Execute multiple commands in sequence on the remote host"""
        # Escape quotes in commands to prevent shell injection
        escaped_commands = []
        for cmd in commands:
            # Escape single quotes by replacing them with '"'"'
            escaped_cmd = cmd.replace("'", "'\"'\"'")
            escaped_commands.append(escaped_cmd)
        
        # Build the combined command with proper escaping
        combined_cmd = " && ".join(escaped_commands)
        
        # Build the SSH command
        ssh_cmd = f"ssh -p {self.ssh_port} {self.ssh_host} 'cd {self.work_dir} && {combined_cmd}'"
        
        if self.verbose:
            print(f"🔧 Executing on {self.ssh_host}:")
            for i, cmd in enumerate(commands, 1):
                print(f"   {i}. {cmd}")
        
        # Execute the commands
        if capture_output:
            result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Command failed: {result.stderr}")
                return result
            else:
                return result
        else:
            return subprocess.run(ssh_cmd, shell=True, text=True)
    
    def execute_script(self, script_content: str, script_name: str = "remote_script.sh") -> subprocess.CompletedProcess:
        """Execute a script on the remote host"""
        try:
            # Create a temporary script file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp_file:
                temp_file.write(script_content)
                temp_script_path = temp_file.name
            
            # Copy script to remote host
            remote_script_path = f"/tmp/{script_name}"
            scp_cmd = f"scp -P {self.ssh_port} {temp_script_path} {self.ssh_host}:{remote_script_path}"
            
            if self.verbose:
                print(f"📤 Uploading script to {self.ssh_host}:{remote_script_path}")
            
            scp_result = subprocess.run(scp_cmd, shell=True, capture_output=True, text=True)
            
            if scp_result.returncode != 0:
                print(f"❌ Failed to upload script: {scp_result.stderr}")
                return scp_result
            
            # Execute the script
            exec_cmd = f"ssh -p {self.ssh_port} {self.ssh_host} 'cd {self.work_dir} && bash {remote_script_path}'"
            
            if self.verbose:
                print(f"🚀 Executing script on {self.ssh_host}")
            
            result = subprocess.run(exec_cmd, shell=True, text=True)
            
            # Clean up remote script
            cleanup_cmd = f"ssh -p {self.ssh_port} {self.ssh_host} 'rm -f {remote_script_path}'"
            subprocess.run(cleanup_cmd, shell=True, capture_output=True)
            
            # Clean up local script
            os.unlink(temp_script_path)
            
            return result
            
        except Exception as e:
            print(f"❌ Error executing script: {e}")
            # Return a failed result
            return subprocess.CompletedProcess(
                args=script_name, 
                returncode=1, 
                stdout="", 
                stderr=str(e)
            )
    
    def check_directory(self, directory: str) -> bool:
        """Check if a directory exists on the remote host"""
        result = self.execute_command(f"test -d {directory}")
        return result.returncode == 0

    def create_directory_by_git(self, github_url: str, directory: str) -> bool:
        """Create a directory on the remote host by cloning a git repository"""
        result = self.execute_command(f"git clone {github_url} {directory}", no_work_dir=True)
        return result.returncode == 0
    
    def create_directory(self, directory: str) -> bool:
        """Create a directory on the remote host"""
        result = self.execute_command(f"mkdir -p {directory}")
        if result.returncode == 0:
            if self.verbose:
                print(f"✅ Created directory: {directory}")
            return True
        else:
            print(f"❌ Failed to create directory: {directory}")
            if self.verbose:
                print(f"   Error: {result.stderr}")
            return False
    
    def check_command_exists(self, command: str) -> bool:
        """Check if a command exists on the remote host"""
        result = self.execute_command(f"which {command}")
        return result.returncode == 0
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload a file to the remote host"""
        scp_cmd = f"scp -P {self.ssh_port} {local_path} {self.ssh_host}:{remote_path}"
        
        if self.verbose:
            print(f"📤 Uploading {local_path} to {self.ssh_host}:{remote_path}")
        
        result = subprocess.run(scp_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            if self.verbose:
                print(f"✅ File uploaded successfully")
            return True
        else:
            print(f"❌ Failed to upload file: {result.stderr}")
            return False
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a file from the remote host"""
        scp_cmd = f"scp -P {self.ssh_port} {self.ssh_host}:{remote_path} {local_path}"
        
        if self.verbose:
            print(f"📥 Downloading {self.ssh_host}:{remote_path} to {local_path}")
        
        result = subprocess.run(scp_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            if self.verbose:
                print(f"✅ File downloaded successfully")
            return True
        else:
            print(f"❌ Failed to download file: {result.stderr}")
            return False


class RemoteTargetExecutor:
    """High-level executor for target operations on remote hosts"""
    
    def __init__(self, target_config: Dict[str, Any], verbose: bool = False):
        """Initialize with target configuration"""
        self.target_config = target_config
        self.verbose = verbose
        
        # Extract SSH and directory information
        self.ssh_host = target_config.get('ssh_host', '')
        self.ssh_port = target_config.get('ssh_port', 22)
        self.work_dir = target_config.get('work_dir', '')
        
        if not self.ssh_host:
            raise ValueError("ssh_host is required for remote target operations")
        
        if not self.work_dir:
            raise ValueError("work_dir is required for remote target operations")
        
        # Create SSH executor
        self.ssh = SSHExecutor(self.ssh_host, self.ssh_port, self.work_dir, verbose)
    
    def validate_connection(self) -> bool:
        """Validate SSH connection and work directory"""
        if not self.ssh.test_connection():
            return False
        
        # Check if work directory exists, create if needed
        if not self.ssh.check_directory(self.work_dir):
            print(f"📁 Work directory {self.work_dir} doesn't exist, creating...")
            return self.ssh.create_directory_by_git(self.target_config.get('github_url', ''), self.work_dir)
        
        return True
    
    def execute_target_operation(self, operation_name: str, commands: List[str]) -> bool:
        """Execute a target operation (init, sync, start) on the remote host"""
        if not self.validate_connection():
            print(f"❌ Failed to validate connection for {operation_name}")
            return False
        
        print(f"🎯 Executing {operation_name} on {self.ssh_host}:{self.work_dir}")
        
        result = self.ssh.execute_commands(commands)
        
        if result.returncode == 0:
            print(f"✅ {operation_name} completed successfully")
            return True
        else:
            print(f"❌ {operation_name} failed")
            return False 