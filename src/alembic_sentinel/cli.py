"""Command-line interface: `alembic-sentinel check migrations/versions`."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markup import escape

from . import __version__
from .linter import lint_paths
from .models import Severity
from .parser import MigrationParseError
from .rules import ALL_RULES

app = typer.Typer(
    help="Catch dangerous PostgreSQL migrations in Alembic before they reach production.",
    no_args_is_help=True,
)
console = Console(soft_wrap=True)
err_console = Console(stderr=True, soft_wrap=True)


class OutputFormat(str, Enum):
    text = "text"
    json = "json"


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"alembic-sentinel {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    """alembic-sentinel."""


@app.command()
def check(
    paths: Annotated[
        list[Path],
        typer.Argument(exists=True, help="Migration files or folders (e.g. migrations/versions)."),
    ],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", "-f", help="Output format.")
    ] = OutputFormat.text,
) -> None:
    """Lint Alembic migration files. Exits with code 1 if any error is found."""
    try:
        violations = lint_paths(paths)
    except MigrationParseError as exc:
        err_console.print(f"[red]error:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    if output_format is OutputFormat.json:
        typer.echo(json.dumps([v.to_dict() for v in violations], indent=2))
    else:
        for v in violations:
            color = "red" if v.severity is Severity.ERROR else "yellow"
            console.print(
                f"[bold]{v.path}:{v.lineno}[/bold] "
                f"[{color}]{v.severity.value}[/{color}] [cyan]{v.rule_id}[/cyan] "
                f"{escape(v.message)}"
            )
            console.print(f"  [dim]hint:[/dim] {escape(v.hint)}\n")
        if violations:
            console.print(f"[bold]{len(violations)} problem(s) found.[/bold]")
        else:
            console.print("[green]No problems found.[/green]")

    if any(v.severity is Severity.ERROR for v in violations):
        raise typer.Exit(code=1)


@app.command("rules")
def list_rules() -> None:
    """List the available rules."""
    for rule in ALL_RULES:
        console.print(f"[cyan]{rule.id}[/cyan] {escape(f'[{rule.severity.value}]')} {rule.summary}")
