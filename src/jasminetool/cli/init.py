import typer
from pathlib import Path
from jasminetool.config import JasmineConfig, save_config
from loguru import logger

def init_jasminetool(
    path: str = typer.Option("./.jasminetool/config.yaml", "--path", "-p", help="Path to the config file"),
    force: bool = typer.Option(False, "--force", "-f", help="Force overwrite the config file")
):
    """
    Initialize a config file at the given path (default: ./.jasminetool/config.yaml)
    """
    if Path(path).exists() and not force:
        logger.warning(f"Config file already exists at {path}, use --force to overwrite")
        return

    if not Path(path).parent.exists():
        logger.info(f"Creating parent directory for {path}")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    
    config = JasmineConfig()
    save_config(config, path)