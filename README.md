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

SSHServer:

K8sServer:

- init: similar to SSH server, will clone the repo and install the dependencies and uv, also install the env vars to the secret
- sync: will assemble commands like `git pull`, `uv sync`
- start: will assemble commands like `uv run sweep & uv run wandb & wait`