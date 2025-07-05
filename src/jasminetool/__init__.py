"""
JasmineTool - Automated multi-GPU/multi-host orchestration via SSH

A configuration-driven task execution system that supports multiple execution modes:
- local: Execute tasks locally
- remote: Execute tasks on remote servers via SSH
- slurm: Submit tasks to SLURM batch system
- remote_gpu: Execute tasks on remote GPU servers with dynamic SSH configuration
"""

from .unified_runner import UnifiedTaskRunner
from .execution_modes import LocalMode, RemoteMode, SlurmMode, RemoteGpuMode
from .utils import TmuxManager, TimeoutInput, ConfigManager, GitManager, CommandExtractor, PreCommandExecutor
from .cli import main as cli_main
from .init import init_jasminetool, JasmineToolInitializer
from .project_init import init_project, ProjectInitializer
from .sync import sync_project, SyncManager
from .version import __version__

__author__ = "suchunsv"
__email__ = "suchunsv@outlook.com"
__license__ = "MIT"
__description__ = "Automated multi-GPU/multi-host orchestration via SSH"

__all__ = [
    "UnifiedTaskRunner",
    "LocalMode",
    "RemoteMode", 
    "SlurmMode",
    "RemoteGpuMode",
    "TmuxManager",
    "TimeoutInput",
    "ConfigManager",
    "GitManager",
    "CommandExtractor",
    "PreCommandExecutor",
    "cli_main",
    "init_jasminetool",
    "JasmineToolInitializer",
    "init_project",
    "ProjectInitializer",
    "sync_project",
    "SyncManager",
] 