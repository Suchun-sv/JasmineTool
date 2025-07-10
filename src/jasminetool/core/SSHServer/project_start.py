from jasminetool.config import JasmineConfig, RemoteSSHConfig
from fabric import Connection
from loguru import logger
import time

class ProjectStarter:
    def __init__(self, global_config: JasmineConfig, connection: Connection, server_config: RemoteSSHConfig):
        self.global_config = global_config
        self.server_config = server_config
        self.conn = connection

    def _with_uv_xcmd_env(self, cmd: str) -> str:
        return f'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$HOME/.x-cmd.root/bin:$PATH" && {cmd}'

    def _has_gpu(self) -> bool:
        result = self.conn.run("command -v nvidia-smi", warn=True, hide=True)
        return result.ok

    def _detect_gpu_count(self) -> int:
        result = self.conn.run("nvidia-smi --query-gpu=name --format=csv,noheader | wc -l", warn=True, hide=True)
        if result.ok:
            try:
                return int(result.stdout.strip())
            except ValueError:
                return 0
        return 0

    def run(self, sweep_id: str, gpu_config: str, num_processes: int, wandb_key: str):
        logger.info(f"🚀 Starting wandb agents on {self.conn.host}")

        # Detect if GPU is available
        has_gpu = self._has_gpu()
        if gpu_config == "0":
            if has_gpu:
                gpu_count = self._detect_gpu_count()
                if gpu_count == 0:
                    logger.warning("⚠ No GPUs detected, using default GPU 0")
                    gpu_ids = ["0"]
                else:
                    gpu_ids = [str(i) for i in range(gpu_count)]
            else:
                logger.warning("⚠ nvidia-smi not found, falling back to CPU-only mode")
                gpu_ids = ["0"]
        else:
            gpu_ids = [g.strip() for g in gpu_config.split(",")]

        short_sweep_id = sweep_id.split("/")[-1] if "/" in sweep_id else sweep_id
        timestamp = time.strftime("%m%d%H%M")
        session_name = f"{short_sweep_id}_{timestamp}"

        result = self.conn.run(f"tmux new-session -d -s {session_name}", warn=True, hide=True)
        if not result.ok:
            logger.error(f"✗ Failed to create tmux session: {session_name}")
            return False

        logger.info(f"📟 Created tmux session: {session_name}")

        first_pane = True
        for gpu_id in gpu_ids:
            for i in range(num_processes):
                if not first_pane:
                    self.conn.run(f"tmux split-window -t {session_name}", warn=True, hide=True)
                    self.conn.run(f"tmux select-layout -t {session_name} tiled", warn=True, hide=True)

                wandb_cmd = f"wandb agent {sweep_id}"
                if has_gpu:
                    full_cmd = f"export WANDB_API_KEY={wandb_key} && CUDA_VISIBLE_DEVICES={gpu_id} {self.server_config.command_runner} {wandb_cmd}"
                else:
                    full_cmd = f"export WANDB_API_KEY={wandb_key} && {self.server_config.command_runner} {wandb_cmd}"

                self.conn.run(f'tmux send-keys -t {session_name} "{self._with_uv_xcmd_env(full_cmd)}" C-m', warn=True, hide=True)
                logger.info(f"✅ Started process {i+1} on GPU {gpu_id}" if has_gpu else f"✅ Started process {i+1} (CPU mode)")

                first_pane = False

        logger.success(f"🎉 All wandb agents started in tmux session: {session_name}")
        logger.info(f"   To view: tmux attach-session -t {session_name}")
        logger.info(f"   To kill: tmux kill-session -t {session_name}")
        return True