import typer
from jasminetool.config import JasmineConfig, load_config
from jasminetool.core import load_server

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

def _check_name(name: str, config: JasmineConfig):
    for server in config.server_config_list:
        if server.name == name:
            return True
    raise ValueError(f"Server config not found for name: {name}")

@target_app.command(name="init")
def init_target(
    name: str = typer.Option(..., "--name", "-n", help="Name of the target"),
    config_path: str = typer.Option(".jasminetool/config.yaml", "--path", "-p", help="Path to the config file"),
):
    """
    Initialize a target server, please specify the name of the target
    """
    config = _init_config(config_path)
    _check_name(name, config)
    server = load_server(name, config)
    server.init()

@target_app.command(name="test")
def test_target(
    name: str = typer.Option(..., "--name", "-n", help="Name of the target"),
    config_path: str = typer.Option(".jasminetool/config.yaml", "--path", "-p", help="Path to the config file"),
):
    """
    Test the target server, please specify the name of the target
    """
    config = _init_config(config_path)
    _check_name(name, config)
    server = load_server(name, config)
    server.test()

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
