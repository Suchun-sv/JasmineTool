import typer
from jasminetool.config import JasmineConfig, load_config
from jasminetool.core import load_server
from typing import List, Union, Optional, Tuple

from jasminetool.cli.util import interactive_select_server_name, get_server_name_list
from jasminetool.core import Server

import rich
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

target_app = typer.Typer(
    name="target",
    help="JasmineTool - Automated multi-GPU/multi-host orchestration via SSH",
    add_completion=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

def _init_config(config_path: str):
    config = load_config(config_path)
    return config

def _check_name(name: Union[str, List[str]], config: JasmineConfig):
    if isinstance(name, str):
        name = [name]
    server_name_list = get_server_name_list(config)
    if not set(name).issubset(set(server_name_list)):
        raise ValueError(f"Server config not found for name: {name}, current available names: {server_name_list}")

def _common_check_and_return_server(config: JasmineConfig, name: Optional[str], interactive: bool) -> Tuple[Server, str]:
    if interactive and name is None:
        name = interactive_select_server_name(config)
    if name is None:
        raise ValueError("Name is required")
    _check_name(name, config)
    server = load_server(name, config)
    return server, name

def _common_check_and_return_server_list(config: JasmineConfig, name: Optional[str], interactive: bool) -> Tuple[List[Server], List[str]]:
    if interactive and name is None:
        name = interactive_select_server_name(config)

    if name is None:
        raise ValueError("Name is required")

    if name == "all":
        name_list = get_server_name_list(config)
    else:
        name_list = [name]

    _check_name(name_list, config)
    server_list = [load_server(name, config) for name in name_list]
    return server_list, name_list

@target_app.command(name="init")
def init_target(
    name: str = typer.Option(None, "--name", "-n", help="Name of the target"),
    config_path: str = typer.Option(".jasminetool/config.yaml", "--path", "-p", help="Path to the config file"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode"),
):
    """
    Initialize a target server, please specify the name of the target
    """
    config = _init_config(config_path)
    if interactive:
        name = interactive_select_server_name(config)
    _check_name(name, config)
    server = load_server(name, config)
    server.init()

@target_app.command(name="check")
def check_target(
    name: str = typer.Option("all", "--name", "-n", help="Name of the target, this command provide `all` as default value"),
    config_path: str = typer.Option(".jasminetool/config.yaml", "--path", "-p", help="Path to the config file"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive mode"),
):
    """
    Test the target server, please specify the name of the target
    """
    config = _init_config(config_path)

    server_list, name_list = _common_check_and_return_server_list(config, name, interactive)
    
    table = Table(title="[bold magenta]Target Check Results[/bold magenta]")
    table.add_column("Name", justify="left", style="cyan", no_wrap=True)
    table.add_column("Mode", justify="left", style="green")
    table.add_column("Status", justify="center")

    for server, name in zip(server_list, name_list):
        status = server.test()
        status_text = Text("✅ SUCCESS", style="green") if status else Text("❌ FAILED", style="red")
        
        # Assuming server object has a config attribute holding its specific config
        mode = server.config.mode if hasattr(server, 'config') and hasattr(server.config, 'mode') else "N/A"
        
        table.add_row(name, mode, status_text)

    rich.print(table)

@target_app.command(name="sync")
def sync_target(
    name: str = typer.Option(..., "--name", "-n", help="Name of the target"),
    config_path: str = typer.Option(".jasminetool/config.yaml", "--path", "-p", help="Path to the config file"),
):
    """
    Synchronize the target server, please specify the name of the target
    """
    config = _init_config(config_path)
    _check_name(name, config)
    server = load_server(name, config)
    server.sync()


@target_app.command(name="start")
def start_target(
    name: str = typer.Option(..., "--name", "-n", help="Name of the target"),
    config_path: str = typer.Option(".jasminetool/config.yaml", "--path", "-p", help="Path to the config file"),
):
    """
    Start the target server, please specify the name of the target
    """
    config = _init_config(config_path)
    _check_name(name, config)
    server = load_server(name, config)
    server.start()
