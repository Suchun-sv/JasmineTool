from pygments.lexer import default
import typer
from jasminetool.config import JasmineConfig, load_config
from jasminetool.core import load_server
from typing import List, Union, Optional, Tuple
from jasminetool.core import SSHServer, K8sServer
import select
import sys

from jasminetool.cli.util import interactive_select_server_name, get_server_name_list, parse_sweep_id
from jasminetool.core import Server

import rich
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

def _prompt_with_timeout(prompt: str, timeout: int) -> Optional[str]:
    rich.print(prompt, end="", flush=True)
    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
    if rlist:
        return sys.stdin.readline().strip()
    else:
        rich.print()  # for a new line after timeout
        return None

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
        raise ValueError("Name is required, use --interactive (-i) to select a target")
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
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive select target by name"),
    force: bool = typer.Option(False, "--force", "-f", help="Force mode"),
):
    """
    Initialize a target server, please specify the name of the target
    """
    config = _init_config(config_path)
    server, name = _common_check_and_return_server(config, name, interactive)
    server.init(force=force)

@target_app.command(name="check")
def check_target(
    name: str = typer.Option("all", "--name", "-n", help="Name of the target, this command provide `all` as default value"),
    config_path: str = typer.Option(".jasminetool/config.yaml", "--path", "-p", help="Path to the config file"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive select target by name"),
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
    table.add_column("Path", justify="center")

    for server, name in zip(server_list, name_list):
        status = server.test()
        status_text = Text("✅ SUCCESS", style="green") if status else Text("❌ FAILED", style="red")

        path_status = server.check_path(server.config.work_dir)
        path_status_text = Text("✅ SUCCESS", style="green") if path_status else Text("❌ FAILED", style="red")
        
        # Assuming server object has a config attribute holding its specific config
        mode = server.config.mode if hasattr(server, 'config') and hasattr(server.config, 'mode') else "N/A"
        
        table.add_row(name, mode, status_text, path_status_text)

    rich.print(table)

# remove the target server
@target_app.command(name="remove", help="Remove the target server word dir")
def remove_target(
    name: str = typer.Option(None, "--name", "-n", help="Name of the target"),
    config_path: str = typer.Option(".jasminetool/config.yaml", "--path", "-p", help="Path to the config file"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Interactive select target by name"),
):
    """
    Remove the target server word dir
    """
    config = _init_config(config_path)
    server, name = _common_check_and_return_server(config, name, interactive)
    server.remove()

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
    if not server.sync():
        raise ValueError("Sync failed, please check the source dir andtarget server")


@target_app.command(name="start")
def start_target(
    name: str = typer.Option(..., "--name", "-n", help="Name of the target"),
    config_path: str = typer.Option(".jasminetool/config.yaml", "--path", "-p", help="Path to the config file"),
    interactive: bool = typer.Option(True, "--interactive", "-i", help="Interactive mode for gpu_config and num_processes"),
):
    """
    Start the target server, please specify the name of the target
    """
    config = _init_config(config_path)
    _check_name(name, config)
    server = load_server(name, config)
    sweep_id = parse_sweep_id(config)

    if server.config.mode == "remote_ssh" and isinstance(server, SSHServer):
        gpu_config = server.server_config.gpu_config
        num_processes = server.server_config.num_processes
        wandb_key = server.gloabl_config.wandb_key

        if interactive:
            rich.print(Panel(
                Text("Entering interactive mode. You have 3 seconds for each prompt.\nPress Enter to use the default value.", justify="center"),
                title="[bold blue]Interactive Configuration[/bold blue]",
                border_style="blue"
            ))

            # Prompt for gpu_config
            user_gpu_config = _prompt_with_timeout(f"Enter GPU config (default: [green]{gpu_config}[/green]): ", 3)
            
            if user_gpu_config is None:
                rich.print(f"Timeout. Using default GPU config: [yellow]{gpu_config}[/yellow]")
            elif user_gpu_config == "":
                rich.print(f"Empty input. Using default GPU config: [yellow]{gpu_config}[/yellow]")
            else:
                gpu_config = user_gpu_config

            # Prompt for num_processes
            user_num_processes = _prompt_with_timeout(f"Enter number of processes (default: [green]{num_processes}[/green]): ", 3)

            if user_num_processes is None:
                rich.print(f"Timeout. Using default number of processes: [yellow]{num_processes}[/yellow]")
            elif user_num_processes == "":
                rich.print(f"Empty input. Using default number of processes: [yellow]{num_processes}[/yellow]")
            else:
                try:
                    num_processes = int(user_num_processes)
                except ValueError:
                    rich.print(f"[red]Invalid input. Expected an integer.[/red] Using default number of processes: [yellow]{server.server_config.num_processes}[/yellow]")
                    num_processes = server.server_config.num_processes
        
        server.start(sweep_id=sweep_id, gpu_config=gpu_config, num_processes=num_processes, wandb_key=wandb_key)
    elif server.config.mode == "remote_k8s" and isinstance(server, K8sServer):
        gpu_config = "0"
        num_processes = server.server_config.num_processes
        wandb_key = server.global_config.wandb_key
        server.start(sweep_id=sweep_id, gpu_config=gpu_config, num_processes=num_processes, wandb_key=wandb_key)
    else:
        raise ValueError(f"Unsupported server Mode: {server.config.mode}")
