import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

import typer
from rich.console import Console
from rich.table import Table
from jasminetool.config import JasmineConfig
from jasminetool.cli.util import get_server_name_list

console = Console()

def install_vscode_tasks(config: JasmineConfig, targets: Optional[List[str]] = None, force: bool = False) -> bool:
    def _ensure_vscode_dir() -> Optional[Path]:
        try:
            path = Path(".vscode")
            path.mkdir(exist_ok=True)
            return path
        except Exception as e:
            console.print(f"[red]✗ Failed to create .vscode directory: {e}[/red]")
            return None

    def _load_tasks(file: Path) -> Optional[Dict[str, Any]]:
        if not file.exists(): return None
        try:
            content = file.read_text(encoding='utf-8')
            content = re.sub(r"//.*", "", content)
            return json.loads(content)
        except Exception as e:
            console.print(f"[yellow]⚠ Failed to parse tasks.json: {e}[/yellow]")
            return None

    def _save_tasks(file: Path, data: Dict[str, Any]) -> bool:
        try:
            file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
            return True
        except Exception as e:
            console.print(f"[red]✗ Failed to save tasks.json: {e}[/red]")
            return False

    def _create_task(label: str, command: str) -> Dict[str, Any]:
        return {
            "label": label,
            "type": "shell",
            "command": command,
            "options": {"cwd": "${workspaceFolder}"},
            "group": {"kind": "build", "isDefault": False},
            "problemMatcher": [],
            "presentation": {"reveal": "always", "panel": "shared"}
        }

    def _create_sweep_start(config: JasmineConfig) -> Optional[Dict[str, Any]]:
        if not getattr(config, 'sweep_file_path', None): return None
        sweep_path = Path(config.sweep_file_path)
        log_path = sweep_path.with_suffix(".log")
        cmd = r"(uv run jasminetool sweep start -f ${file} 2>&1)" + f" | tee {log_path}"
        return _create_task("wandb sweep", cmd)

    def _create_parallel_all(targets: List[str]) -> Dict[str, Any]:
        return {
            "label": "sweep [all]",
            "dependsOn": [f"sweep {t}" for t in targets],
            "dependsOrder": "parallel",
            "group": {"kind": "build", "isDefault": False},
            "problemMatcher": [],
            "presentation": {"reveal": "always", "panel": "shared"}
        }

    vscode_dir = _ensure_vscode_dir()
    if not vscode_dir:
        return False
    tasks_file = vscode_dir / "tasks.json"
    tasks_data = _load_tasks(tasks_file) or {"version": "2.0.0", "tasks": []}
    tasks_data.setdefault("tasks", [])
    existing_labels = {t.get("label") for t in tasks_data["tasks"]}

    if targets is None:
        targets = get_server_name_list(config)

    table = Table(title="VS Code Task Install Summary", header_style="bold magenta")
    table.add_column("Label")
    table.add_column("Status")

    added = 0
    skipped = 0
    updated = 0

    with typer.progressbar(targets, label="Installing sweep target tasks...") as bar:
        for target in bar:
            label = f"sweep {target}"
            task = _create_task(label, f"uv run jt target sync -n {target} && uv run jt target start -n {target}")
            if label in existing_labels and not force:
                table.add_row(label, "[yellow]skipped[/yellow]")
                skipped += 1
                continue
            if label in existing_labels:
                tasks_data["tasks"] = [t for t in tasks_data["tasks"] if t.get("label") != label]
                updated += 1
            else:
                added += 1
            tasks_data["tasks"].append(task)
            table.add_row(label, "[green]installed[/green]")

    if len(targets) > 1:
        all_label = "sweep [all]"
        all_task = _create_parallel_all(targets)
        if all_label not in existing_labels or force:
            tasks_data["tasks"] = [t for t in tasks_data["tasks"] if t.get("label") != all_label]
            tasks_data["tasks"].append(all_task)
            table.add_row(all_label, "[green]installed[/green]")

    sweep_task = _create_sweep_start(config)
    if sweep_task:
        label = sweep_task["label"]
        if label not in existing_labels or force:
            tasks_data["tasks"] = [t for t in tasks_data["tasks"] if t.get("label") != label]
            tasks_data["tasks"].append(sweep_task)
            table.add_row(label, "[green]installed[/green]")
        else:
            table.add_row(label, "[yellow]skipped[/yellow]")

    success = _save_tasks(tasks_file, tasks_data)
    if success:
        console.print(table)
        console.print(f"\n[bold green]✅ VS Code tasks updated ({added} added, {updated} overwritten, {skipped} skipped)[/bold green]")
        console.print("[blue]💡 Press Cmd/Ctrl+Shift+P → Tasks: Run Task to try them out[/blue]")
        return True
    else:
        console.print("[red]❌ Failed to write tasks.json[/red]")
        return False