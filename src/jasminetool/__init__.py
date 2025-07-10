"""
JasmineTool - Automated multi-GPU/multi-host orchestration via SSH

A configuration-driven task execution system that supports multiple execution modes:
- local: Execute tasks locally
- remote: Execute tasks on remote servers via SSH
- slurm: Submit tasks to SLURM batch system
- remote_gpu: Execute tasks on remote GPU servers with dynamic SSH configuration
"""

from .cli import main as cli_main
from .version import __version__

__author__ = "suchunsv"
__email__ = "suchunsv@outlook.com"
__license__ = "MIT"
__description__ = "Automated multi-GPU/multi-host orchestration via SSH"

__all__ = [
    "cli_main",
] 