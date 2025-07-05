#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Command Line Interface for JasmineTool

This module provides the main entry point for the JasmineTool CLI.
"""

import sys
import argparse
from typing import List, Optional

from .unified_runner import UnifiedTaskRunner
from .init import init_jasminetool
from .project_init import init_project
from .sync import sync_project
from .config_display import display_config
from .version import __version__


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI"""
    parser = argparse.ArgumentParser(
        prog="jasminetool",
        description="JasmineTool - Automated multi-GPU/multi-host orchestration via SSH",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  jasminetool init                           # Initialize the configuration file
  jasminetool config                         # Display the configuration file
  jasminetool -t test_ubuntu config         # Display configuration for specific target
  jasminetool -t test_ubuntu init           # Initialize project for target
  jasminetool -t test_ubuntu sync           # Synchronize project for target
  jasminetool local_gpu                      # Run on local GPU
  jasminetool remote_server --config ./my_config.yaml  # Run on remote server
  jasminetool slurm_cluster --skip-confirmation       # Submit to SLURM
  jasminetool remote_gpu --skip-interactive           # Run on remote GPU servers
        """
    )
    
    parser.add_argument(
        "action",
        nargs="?",
        help="Action to perform: 'init' (initialize config), 'config' (display config), 'sync' (sync project), target name (execute target), or use with -t flag"
    )
    
    parser.add_argument(
        "-t", "--target",
        help="Target configuration name (use with 'init' or 'sync' actions)"
    )
    
    parser.add_argument(
        "--config",
        default="./.jasminetool/config.yaml",
        help="Path to configuration file (default: ./.jasminetool/config.yaml)"
    )
    
    parser.add_argument(
        "--skip-confirmation",
        action="store_true",
        help="Skip execution confirmation prompt"
    )
    
    parser.add_argument(
        "--skip-interactive",
        action="store_true",
        help="Skip interactive configuration update"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force initialization even if already initialized (for init command)"
    )
    
    return parser


def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI"""
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    # Handle different command patterns
    action = parsed_args.action
    target = parsed_args.target
    
    # Pattern 1: jasminetool init (initialize JasmineTool configuration)
    if action == "init" and not target:
        if parsed_args.verbose:
            print("Initializing JasmineTool configuration...")
        
        try:
            success = init_jasminetool(
                base_dir=".",
                force=parsed_args.force,
                verbose=parsed_args.verbose
            )
            return 0 if success else 1
        except KeyboardInterrupt:
            print("\nInitialization cancelled by user", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Initialization failed: {e}", file=sys.stderr)
            if parsed_args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    # Pattern 2: jasminetool config (display configuration)
    elif action == "config":
        if parsed_args.verbose:
            if target:
                print(f"Displaying configuration for target: {target}")
            else:
                print("Displaying configuration file...")
        
        try:
            success = display_config(
                config_path=parsed_args.config,
                target=target,
                verbose=parsed_args.verbose
            )
            return 0 if success else 1
        except KeyboardInterrupt:
            print("\nConfig display cancelled by user", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Config display failed: {e}", file=sys.stderr)
            if parsed_args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    # Pattern 3: jasminetool -t target init (initialize project for target)
    elif action == "init" and target:
        if parsed_args.verbose:
            print(f"Initializing project for target: {target}")
        
        try:
            success = init_project(
                config_path=parsed_args.config,
                target=target,
                verbose=parsed_args.verbose
            )
            return 0 if success else 1
        except KeyboardInterrupt:
            print("\nProject initialization cancelled by user", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Project initialization failed: {e}", file=sys.stderr)
            if parsed_args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    # Pattern 4: jasminetool -t target sync (synchronize project for target)
    elif action == "sync" and target:
        if parsed_args.verbose:
            print(f"Synchronizing project for target: {target}")
        
        try:
            success = sync_project(
                config_path=parsed_args.config,
                target=target,
                verbose=parsed_args.verbose
            )
            return 0 if success else 1
        except KeyboardInterrupt:
            print("\nProject synchronization cancelled by user", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Project synchronization failed: {e}", file=sys.stderr)
            if parsed_args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    # Pattern 5: jasminetool target (execute target configuration)
    elif action and not target:
        target_name = action  # action is actually the target name
        
        if parsed_args.verbose:
            print(f"JasmineTool starting with target: {target_name}")
            print(f"Configuration file: {parsed_args.config}")
        
        # Create and run the task runner
        runner = UnifiedTaskRunner(parsed_args.config)
        
        # Load configuration
        if not runner.load_configuration():
            print("Error: Failed to load configuration", file=sys.stderr)
            print("Use 'jasminetool init' to create a default configuration", file=sys.stderr)
            return 1
        
        # Execute the target
        try:
            success = runner.execute_target(
                target_name,
                skip_confirmation=parsed_args.skip_confirmation,
                skip_interactive=parsed_args.skip_interactive
            )
            
            if success:
                print("Task completed successfully!")
                return 0
            else:
                print("Task failed!", file=sys.stderr)
                return 1
                
        except KeyboardInterrupt:
            print("\nOperation cancelled by user", file=sys.stderr)
            return 1
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            if parsed_args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    # Pattern 6: No action provided or invalid combination
    else:
        print("Error: Action is required", file=sys.stderr)
        print("Usage:", file=sys.stderr)
        print("  jasminetool init                    # Initialize JasmineTool configuration", file=sys.stderr)
        print("  jasminetool config                  # Display configuration file", file=sys.stderr)
        print("  jasminetool -t target config        # Display configuration for specific target", file=sys.stderr)
        print("  jasminetool -t target init          # Initialize project for target", file=sys.stderr)
        print("  jasminetool -t target sync          # Synchronize project for target", file=sys.stderr)
        print("  jasminetool target                  # Execute target configuration", file=sys.stderr)
        print("  jasminetool --help                  # Show help", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 