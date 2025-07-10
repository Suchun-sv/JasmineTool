#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Command Line Interface for JasmineTool (Typer-based)

This module provides the main entry point for the JasmineTool CLI using Typer.
"""

import sys
import traceback
from typing import List, Optional

import typer
from typing_extensions import Annotated

from .init import init_jasminetool
from .target import target_app

# Main Typer application
app = typer.Typer(
    name="jasminetool",
    help="JasmineTool - Automated multi-GPU/multi-host orchestration via SSH",
    add_completion=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

app.command(name="init")(init_jasminetool)
app.add_typer(target_app, name="target")

def main():
    """Main entry point for the CLI."""
    app()

# Add the main entry point for the script
if __name__ == "__main__":
    main()