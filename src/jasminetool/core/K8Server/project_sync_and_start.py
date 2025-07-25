from jasminetool.config import JasmineConfig, RemoteK8sConfig
import subprocess
from loguru import logger

class ProjectSyncAndStart:
    def __init__(self, global_config: JasmineConfig, server_config: RemoteK8sConfig):
        self.global_config = global_config
        self.server_config = server_config
        self.src_dir = global_config.src_dir

    def _with_env_vars(self, cmd: str) -> str:
        base_cmd = cmd
        for key, value in self.global_config.env_vars.items():
            base_cmd = f'export {key}={value} && {base_cmd}'
        return base_cmd
    
    def run(self, num_processes: int, sweep_id: str) -> str:
        sync_script = self.sync()
        start_script = self.start(num_processes, sweep_id)
        bash_header = "#!/bin/bash\n\n"
        return bash_header + sync_script + "\n" + start_script

    def sync(self) -> str:
        """
        Only need to reset to the target branch && commit
        """
        if not self._check_git_clean():
            raise ValueError("Git repo is not clean")

        # get the current branch
        branch = self._get_current_branch()
        if branch is None:
            raise ValueError("Failed to get current branch")

        # sync the git branch one the target branch, writing bash script
        sync_script = f"""
echo "Syncing git branch {branch}..." && \
cd {self.server_config.work_dir} && \
{self._with_env_vars("git fetch --all && ")}
{self._with_env_vars(f"git checkout {branch} || git checkout -b {branch} origin/{branch} && ")}
{self._with_env_vars(f"git reset --hard origin/{branch} && ")}
echo "✓ Git branch {branch} synced"
"""
        return sync_script

    def start(self, num_processes: int, sweep_id: str):
        """
        Generate start script with automatic GPU detection and multi-process support
        
        Args:
            num_processes: Number of processes per GPU
            sweep_id: WandB sweep ID for agent mode
            
        Returns:
            Bash script string
        """
        return self._generate_start_script(num_processes, sweep_id)
    
    def _generate_start_script(self, num_processes: int, sweep_id: str) -> str:
        """
        Generate a bash script that automatically detects GPU count and starts multiple processes
        
        Args:
            num_processes: Number of processes per GPU
            sweep_id: WandB sweep ID for agent mode
            
        Returns:
            Bash script string
        """
        # Base command
        wandb_cmd = self._with_env_vars(f"uv run wandb agent {sweep_id}")
        base_cmd = f"cd {self.server_config.work_dir} && export WANDB_API_KEY={self.global_config.wandb_key} && {wandb_cmd}"
        
        # Generate the bash script with GPU detection and multi-process logic
        script = f"""#!/bin/bash

# Auto-detect GPU count and start multiple processes
echo "🔍 Detecting GPU count..."

# Function to get GPU count using nvidia-smi
get_gpu_count() {{
    if command -v nvidia-smi &> /dev/null; then
        gpu_count=$(nvidia-smi --list-gpus | wc -l)
        echo "Found $gpu_count GPU(s)" >&2
        echo $gpu_count
    else
        echo "No nvidia-smi found, assuming CPU-only mode" >&2
        echo 0
    fi
}}

# Function to get CUDA_VISIBLE_DEVICES environment variable name
get_cuda_var_name() {{
    # Try different possible names for CUDA_VISIBLE_DEVICES
    if [ -n "$CUDA_VISIBLE_DEVICES" ]; then
        echo "CUDA_VISIBLE_DEVICES"
    elif [ -n "$CUDA_DEVICE_ORDER" ]; then
        echo "CUDA_VISIBLE_DEVICES"
    else
        echo "CUDA_VISIBLE_DEVICES"
    fi
}}

# Get GPU count
gpu_count=$(get_gpu_count)
cuda_var=$(get_cuda_var_name)

echo "📊 Configuration:"
echo "  - GPU count: $gpu_count"
echo "  - Processes per GPU: {num_processes}"
echo "  - Total processes: $((gpu_count * {num_processes}))"

# Calculate total processes
total_processes=$((gpu_count * {num_processes}))

if [ "$gpu_count" -eq 0 ]; then
    echo "🖥️  CPU-only mode detected"
    # Start multiple processes for CPU mode
    echo "🚀 Starting {num_processes} processes in CPU mode..."
    
    # Start multiple processes for CPU mode
    for ((i=0; i<{num_processes}; i++)); do
        echo "🚀 Starting process $((i+1))/{num_processes} in CPU mode..."
        
        # Start the process without GPU assignment
        {base_cmd} &
        
        # Store the process ID
        pids[$i]=$!
        echo "Process $((i+1)) started with PID ${{pids[$i]}}"
    done
    
    echo "⏳ Waiting for all processes to complete..."
    # Wait for all background processes to complete
    for pid in "${{pids[@]}}"; do
        wait $pid
    done
    echo "✅ All processes completed"
else
    echo "🎮 GPU mode detected with $gpu_count GPU(s)"
    
    # Start multiple processes with GPU assignment
    for ((i=0; i<total_processes; i++)); do
        # Calculate which GPU this process should use
        gpu_id=$((i % gpu_count))
        
        echo "🚀 Starting process $((i+1))/$total_processes on GPU $gpu_id..."
        
        # Set CUDA_VISIBLE_DEVICES and start the process
        export $cuda_var=$gpu_id
        {base_cmd} &
        
        # Store the process ID
        pids[$i]=$!
        echo "Process $((i+1)) started with PID ${{pids[$i]}}"
    done
    
    echo "⏳ Waiting for all processes to complete..."
    # Wait for all background processes to complete
    for pid in "${{pids[@]}}"; do
        wait $pid
    done
    echo "✅ All processes completed"
fi

echo "🎉 Job execution finished"
"""
        return script
        

    def _check_git_clean(self) -> bool:
        res = subprocess.run(f"cd {self.src_dir} && git status --porcelain", shell=True, capture_output=True)
        if res.stdout.strip():
            logger.error(f"✗ Source repo not clean:\n{res.stdout}")
            return False
        else:
            logger.info(f"✓ Source repo is clean")
        return True
    
    def _get_current_branch(self) -> str | None:
        res = subprocess.run(f"cd {self.src_dir} && git rev-parse --abbrev-ref HEAD", shell=True, capture_output=True)
        if res.returncode != 0:
            logger.error(f"✗ Failed to get current branch:\n{res.stderr}")
            return None
        branch = res.stdout.strip().decode()
        logger.info(f"✓ Current branch: {branch}")
        return branch