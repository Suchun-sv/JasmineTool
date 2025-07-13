from jasminetool.config import JasmineConfig, RemoteSSHConfig
from fabric import Connection
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import time

class ProjectStarter:
    def __init__(self, global_config: JasmineConfig, connection: Connection, server_config: RemoteSSHConfig):
        self.global_config = global_config
        self.server_config = server_config
        self.conn = connection
        self.console = Console()

    def _with_env(self, cmd: str) -> str:
        env_cmd = ""
        if hasattr(self.global_config, "env_vars") and self.global_config.env_vars:
            env_vars = self.global_config.env_vars
            for key, value in env_vars.items():
                env_cmd += f'export {key}="{value}" && '
        return f'{env_cmd}export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$HOME/.x-cmd.root/bin:$PATH" && {cmd}'

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

    def _generate_session_name(self, sweep_id: str) -> str:
        short_sweep_id = sweep_id.split("/")[-1] if "/" in sweep_id else sweep_id
        timestamp = time.strftime("%m%d%H%M")
        return f"{short_sweep_id}_{timestamp}"

    def _print_summary(self, session_name: str, gpu_ids: list, num_processes: int, has_gpu: bool):
        table = Table(title="[bold green]WandB Agent Launch Summary[/bold green]", box=box.SIMPLE)
        table.add_column("Item", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")

        table.add_row("Session Name", session_name)
        table.add_row("GPU IDs", ", ".join(gpu_ids))
        table.add_row("Processes per GPU", str(num_processes))
        table.add_row("GPU Mode", "Yes" if has_gpu else "No (CPU-only)")

        self.console.print(table)
    
    def _get_gpu_ids(self, gpu_config: str, has_gpu: bool) -> list[str]:
        if gpu_config == "0":
            if has_gpu:
                gpu_count = self._detect_gpu_count()
                gpu_ids = [str(i) for i in range(gpu_count)] if gpu_count > 0 else ["0"]
                if gpu_count == 0:
                    self.console.print("[yellow]⚠ No GPUs detected, defaulting to GPU 0[/yellow]")
                return gpu_ids
            else:
                self.console.print("[yellow]⚠ nvidia-smi not found, using CPU-only mode[/yellow]")
                return ["0"]
        else:
            return [g.strip() for g in gpu_config.split(",")]

    def run(self, sweep_id: str, gpu_config: str, num_processes: int, wandb_key: str):
        self.console.rule(f"🚀 Starting wandb agents on [bold blue]{self.conn.host}[/bold blue]")

        has_gpu = self._has_gpu()
        gpu_ids = self._get_gpu_ids(gpu_config, has_gpu)

        session_name = self._generate_session_name(sweep_id)

        result = self.conn.run(f"tmux new-session -d -s {session_name}", warn=True, hide=True)
        if not result.ok:
            self.console.print(f"[bold red]✗ Failed to create tmux session: {session_name}[/bold red]")
            return False

        self.console.print(f"[green]📟 Created tmux session:[/green] {session_name}")
        self._print_summary(session_name, gpu_ids, num_processes, has_gpu)

        first_pane = True
        for gpu_id in gpu_ids:
            for i in range(num_processes):
                if not first_pane:
                    self.conn.run(f"tmux split-window -t {session_name}", warn=True, hide=True)
                    self.conn.run(f"tmux select-layout -t {session_name} tiled", warn=True, hide=True)

                wandb_cmd = f"wandb agent {sweep_id}"
                base_cmd = f"cd {self.server_config.work_dir} && export WANDB_API_KEY={wandb_key} && "
                if has_gpu:
                    full_cmd = f"{base_cmd}CUDA_VISIBLE_DEVICES={gpu_id} {self.server_config.command_runner} {wandb_cmd}"
                else:
                    full_cmd = f"{base_cmd}{self.server_config.command_runner} {wandb_cmd}"

                final_cmd = self._with_env(full_cmd)
                self.conn.run(f'tmux send-keys -t {session_name} "{final_cmd}" C-m', warn=True, hide=True)

                msg = f"✅ Started process {i+1} on GPU {gpu_id}" if has_gpu else f"✅ Started process {i+1} (CPU-only)"
                self.console.print(f"[bold green]{msg}[/bold green]")
                first_pane = False

        self.console.print(Panel.fit(
            f"🎉 All wandb agents started in tmux session: [bold cyan]{session_name}[/bold cyan]\n"
            f"[green]View:[/green] {self._get_remote_view_cmd(session_name)}\n"
            f"[red]Kill:[/red] {self._get_remote_kill_cmd(session_name)}",
            title="[bold blue]Finished[/bold blue]",
            border_style="green"
        ))
        return True
    
    def _get_remote_view_cmd(self, session_name: str) -> str:
        user_name, server_ip = self.server_config.user_name, self.server_config.server_ip
        return f"ssh {user_name}@{server_ip} -t 'tmux attach-session -t {session_name}'"
    
    def _get_remote_kill_cmd(self, session_name: str) -> str:
        user_name, server_ip = self.server_config.user_name, self.server_config.server_ip
        return f"ssh {user_name}@{server_ip} -t 'tmux kill-session -t {session_name}'"
    
    