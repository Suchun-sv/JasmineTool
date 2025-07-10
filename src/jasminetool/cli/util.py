from rich import print
from rich.prompt import Prompt
from rich.table import Table
from pathlib import Path
from jasminetool.config import JasmineConfig, BaseConfig
from typing import List

def interactive_select_server_name(config: JasmineConfig) -> str:
    server_list = get_server_list(config)
    name_list = get_server_name_list(config)

    table = Table(title="Available Targets")
    table.add_column("Index", style="cyan", justify="right")
    table.add_column("Target Name", style="magenta")
    table.add_column("Mode", style="green")

    for idx, server in enumerate(server_list):
        table.add_row(str(idx), server.name, server.mode)

    print(table)

    while True:
        try:
            idx = int(Prompt.ask("Please select a target by index", choices=[str(i) for i in range(len(name_list))]))
            return name_list[idx]
        except (ValueError, IndexError):
            print("[red]Invalid selection. Please choose a valid index.[/red]")

def get_server_list(config: JasmineConfig) -> List[BaseConfig]:
    return [server for server in config.server_config_list]

def get_server_name_list(config: JasmineConfig) -> List[str]:
    return [server.name for server in config.server_config_list]

def parse_sweep_id(config: JasmineConfig) -> str:
    sweep_file_path = Path(config.sweep_file_path)
    if not sweep_file_path.exists():
        raise ValueError(f"Sweep file not found: {sweep_file_path}")

    with open(sweep_file_path, "r") as f:
        content = f.read()

    lines = content.strip().split('\n')
    for line in lines:
        if 'wandb agent' in line and 'Run sweep agent with:' in line:
            parts = line.split('wandb agent')
            if len(parts) > 1:
                sweep_id = parts[-1].strip()
                return sweep_id
    raise ValueError(f"No sweep ID found in the sweep file: {config.sweep_file_path}")