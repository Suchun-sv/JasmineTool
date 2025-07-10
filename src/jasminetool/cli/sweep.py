import typer
import yaml
from pathlib import Path
import subprocess

sweep_app = typer.Typer(name="sweep")

@sweep_app.command(name="start")
def start_sweep(
    file_path: str = typer.Option(..., "--file", "-f", help="The path to the sweep file")
):
    sweep_file_path = Path(file_path)
    sweep_file_name = sweep_file_path.name
    if sweep_file_name.endswith(".yaml"):
        sweep_file_name = sweep_file_name[:-5]
    if sweep_file_name.endswith(".yml"):
        sweep_file_name = sweep_file_name[:-4]

    # change the name in the yaml file to the name of the sweep file
    with open(sweep_file_path, "r") as f:
        sweep_config = yaml.safe_load(f)
    sweep_config["name"] = sweep_file_name
    with open(sweep_file_path, "w") as f:
        yaml.dump(sweep_config, f)

    # run the sweep
    full_cmd = f"wandb sweep {sweep_file_path}"
    subprocess.run(full_cmd, shell=True)