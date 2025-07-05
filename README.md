# JasmineTool

**JasmineTool** is an automated multi-GPU/multi-host orchestration tool that enables seamless distributed execution of Wandb Sweep agents across different computing environments via SSH and other protocols.

## Features

🚀 **Multi-Mode Execution**: Support for local, remote, SLURM cluster, and multi-server GPU execution  
🔧 **Flexible Configuration**: YAML-based configuration with target-specific settings  
🌐 **SSH Orchestration**: Remote execution with automatic Git synchronization and DVC support  
⚡ **Parallel Processing**: Automatic GPU allocation and process management with tmux sessions  
🎯 **Wandb Integration**: Seamless integration with Wandb Sweep for hyperparameter optimization  
🔄 **VS Code Integration**: Built-in task generation for VS Code development workflow  
📦 **DVC Support**: Integrated data version control and remote cache management  

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/JasmineTool.git
cd JasmineTool

# Install with uv (recommended)
uv venv
uv sync

# Or install with pip
pip install -e .
```

### Dependencies

- Python >= 3.8
- PyYAML >= 5.4.0
- Wandb >= 0.21.0
- SSH client (for remote execution)
- tmux (for session management)
- Git (for synchronization)
- DVC (optional, for data version control)

## Quick Start

### 1. Initialize Configuration

```bash
# Initialize JasmineTool configuration
jt init

# Initialize for a specific target
jt init -t my_target
```

This creates `.jasminetool/config.yaml` with your project configuration.

### 2. Configure Targets

Edit `.jasminetool/config.yaml` to define your execution targets:

```yaml
# Global settings
sweep_file: ".jasminetool/sweep_config.yaml"
pattern: "wandb agent"
wandb_key: "your_wandb_api_key"

# Local execution target
local_gpu:
  mode: local
  gpu_config: "0,1,2,3"
  num_processes: 2

# Remote server target
remote_server:
  mode: remote
  ssh_host: "user@remote-server.com"
  work_dir: "/path/to/project"
  github_url: "git@github.com:user/repo.git"
  gpu_config: "0,1"
  num_processes: 1
  dvc_cache: "/path/to/dvc/cache"
  dvc_remote: "s3://my-bucket/dvc-cache/"

# SLURM cluster target
slurm_cluster:
  mode: slurm
  gpu_config: "0,1,2,3"
  num_processes: 2
  slurm_config:
    job-name: "jasmine-sweep"
    time: "24:00:00"
    nodes: 1
    gres: "gpu:4"
    partition: "gpu"
```

### 3. Create Wandb Sweep

```bash
# Create a wandb sweep configuration
jt sweep --config sweep_config.yaml

# Or install wandb sweep command to VS Code tasks
jt sweep --install
```

### 4. Execute Targets

```bash
# Display target configuration
jt -t remote_server config

# Initialize project on target
jt -t remote_server init

# Sync project to target
jt -t remote_server sync

# Start execution
jt -t remote_server start

# Or execute directly
jt remote_server
```

## Execution Modes

### Local Mode

Execute tasks on the local machine with GPU allocation:

```yaml
local_target:
  mode: local
  gpu_config: "0,1,2,3"  # GPU IDs to use
  num_processes: 2       # Processes per GPU
```

### Remote Mode

Execute tasks on remote servers via SSH:

```yaml
remote_target:
  mode: remote
  ssh_host: "user@server.com"
  work_dir: "/remote/project/path"
  github_url: "git@github.com:user/repo.git"
  gpu_config: "0,1"
  num_processes: 1
  sync_method: "git"     # or "rsync"
  git_operations:
    - "git fetch origin"
    - "git checkout {branch}"
    - "git pull origin {branch}"
```

### SLURM Mode

Submit jobs to SLURM batch system:

```yaml
slurm_target:
  mode: slurm
  gpu_config: "0,1,2,3"
  num_processes: 2
  slurm_config:
    job-name: "jasmine-job"
    time: "24:00:00"
    nodes: 1
    ntasks-per-node: 4
    gres: "gpu:4"
    partition: "gpu"
```

### Remote GPU Mode

Execute on multiple remote GPU servers with failover:

```yaml
remote_gpu_target:
  mode: remote_gpu
  servers:
    - ssh_host: "user@gpu1.com"
      work_dir: "/project/path"
      gpu_config: "0,1"
      num_processes: 1
    - ssh_host: "user@gpu2.com"
      work_dir: "/project/path"
      gpu_config: "0,1,2,3"
      num_processes: 2
```

## Command Reference

### Core Commands

```bash
# Initialize configuration
jt init                    # Initialize JasmineTool config
jt init -t target         # Initialize project for target

# Configuration management
jt config                 # Display all configurations
jt -t target config       # Display target configuration

# Project synchronization
jt -t target sync         # Sync project to target

# Execution
jt -t target start        # Start wandb agents
jt target                 # Direct execution

# Wandb sweep management
jt sweep --config file    # Create wandb sweep
jt sweep --install        # Install sweep to VS Code

# VS Code integration
jt install                # Install all target tasks
jt -t target install      # Install specific target task
```

### Advanced Options

```bash
# Skip confirmations
jt target --skip-confirmation

# Skip interactive updates
jt target --skip-interactive

# Verbose output
jt -t target start -v

# Force operations
jt init --force
jt sweep --install --force
```

## Configuration File Structure

### Global Configuration

```yaml
# .jasminetool/config.yaml
sweep_file: ".jasminetool/sweep_config.yaml"  # Wandb sweep config file
pattern: "wandb agent"                        # Command pattern to extract
wandb_key: "your_wandb_api_key"              # Wandb API key
src_dir: "/path/to/source"                   # Source directory
```

### Target Configuration

```yaml
target_name:
  mode: "local|remote|slurm|remote_gpu"      # Execution mode
  gpu_config: "0,1,2,3"                      # GPU configuration
  num_processes: 2                           # Number of processes
  
  # Remote-specific settings
  ssh_host: "user@server.com"                # SSH connection string
  work_dir: "/remote/project/path"           # Remote working directory
  github_url: "git@github.com:user/repo.git" # Git repository URL
  
  # DVC settings
  dvc_cache: "/path/to/dvc/cache"            # DVC cache directory
  dvc_remote: "s3://bucket/dvc-cache/"       # DVC remote storage
  
  # Synchronization settings
  sync_method: "git|rsync"                   # Sync method
  git_operations:                            # Git commands to run
    - "git fetch origin"
    - "git checkout {branch}"
    - "git pull origin {branch}"
  
  # Pre-execution commands
  pre_commands:
    - command: "echo 'Starting execution'"
      working_dir: "."
    - command: "nvidia-smi"
      working_dir: "."
```

## VS Code Integration

JasmineTool provides seamless VS Code integration through task generation:

### Install Tasks

```bash
# Install all target tasks
jt install

# Install specific target task
jt -t target install

# Install wandb sweep task
jt sweep --install
```

### Generated Tasks

The tool generates tasks in `.vscode/tasks.json`:

- `sweep target`: Sync and start execution for target
- `wandb sweep`: Create wandb sweep from configuration
- Individual target tasks for each configured target

### Debug Configuration

VS Code launch configurations are provided in `.vscode/launch.json` for debugging:

- JasmineTool CLI debugging
- Target-specific debugging
- Verbose execution debugging

## Examples

### Example 1: Local GPU Training

```yaml
local_training:
  mode: local
  gpu_config: "0,1"
  num_processes: 1
```

```bash
jt -t local_training start
```

### Example 2: Remote Server with DVC

```yaml
remote_with_dvc:
  mode: remote
  ssh_host: "user@ml-server.com"
  work_dir: "/home/user/project"
  github_url: "git@github.com:user/ml-project.git"
  gpu_config: "0,1,2,3"
  num_processes: 2
  dvc_cache: "/mnt/storage/dvc-cache"
  dvc_remote: "s3://ml-data-bucket/cache/"
```

```bash
jt -t remote_with_dvc sync
jt -t remote_with_dvc start
```

### Example 3: SLURM Cluster

```yaml
hpc_cluster:
  mode: slurm
  gpu_config: "0,1,2,3"
  num_processes: 4
  slurm_config:
    job-name: "hyperparameter-sweep"
    time: "48:00:00"
    nodes: 2
    ntasks-per-node: 4
    gres: "gpu:4"
    partition: "gpu-long"
    constraint: "v100"
```

```bash
jt hpc_cluster
```

## Advanced Features

### Git Integration

- Automatic branch detection and synchronization
- Clean repository validation
- Remote git operations with branch substitution

### DVC Integration

- Automatic DVC cache configuration
- Remote storage synchronization
- Data pipeline management

### Tmux Session Management

- Automatic session creation and management
- GPU-specific session allocation
- Process monitoring and logging

### Error Handling

- SSH connection testing and failover
- Git repository validation
- Configuration validation and error reporting

## Troubleshooting

### Common Issues

1. **SSH Connection Failed**
   ```bash
   # Test SSH connection
   ssh user@server.com echo "test"
   
   # Check SSH key configuration
   ssh-add -l
   ```

2. **Git Repository Issues**
   ```bash
   # Check git status
   git status
   
   # Ensure clean repository
   git stash
   ```

3. **DVC Cache Issues**
   ```bash
   # Check DVC configuration
   dvc cache dir
   
   # Verify remote access
   dvc remote list
   ```

### Debug Mode

Enable verbose output for debugging:

```bash
jt -t target start -v
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: Report bugs and request features on [GitHub Issues](https://github.com/yourusername/JasmineTool/issues)
- **Documentation**: Check the source code for detailed implementation
- **Community**: Join discussions and share experiences

## Changelog

### Version 0.1.0

- Initial release with multi-mode execution support
- SSH orchestration with Git and DVC integration
- VS Code integration with task generation
- Wandb Sweep automation
- Comprehensive configuration management
