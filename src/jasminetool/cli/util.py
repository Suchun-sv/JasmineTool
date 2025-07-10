from rich import print
from rich.prompt import Prompt
from rich.table import Table
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