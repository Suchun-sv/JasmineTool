import typer
from jasminetool.install import install_vscode_tasks
from jasminetool.config import load_config
from .util import get_server_name_list

# install_app = typer.Typer()

# (wandb sweep ${file} 2>&1) | tee .jasminetool/sweep_config.yaml
# SWEEP_TEMPLATE = "(uv run jt sweep start -f {} 2>&1) | tee {sweep_config_path}"
# TASK_COMMAND_TEMPLATE = "uv run jt target sync -n {target} && uv run jt target start -n {target}"


install_app = typer.Typer()

@install_app.command("all")
def install_target(
    config_path: str = typer.Option(".jasminetool/config.yaml", "--path", "-p", help="Path to the config file"),
    force: bool = typer.Option(False, "--force", "-f", help="Force install"),
):
    typer.echo("Installing target...")
    config = load_config(config_path)
    targets = get_server_name_list(config)
    install_vscode_tasks(config, targets, force)
