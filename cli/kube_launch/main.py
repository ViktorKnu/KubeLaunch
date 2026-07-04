"""KubeLaunch CLI commands."""

import typer

from kube_launch.prerequisites import ToolStatus, check_tools

app = typer.Typer(
    name="kube-launch",
    help="Bootstrap and inspect a local GitOps-native Kubernetes platform.",
    no_args_is_help=True,
)


def _print_tool_statuses(statuses: list[ToolStatus]) -> bool:
    """Print prerequisite results and return whether every tool is available."""
    typer.echo("Prerequisites:")
    for status in statuses:
        if status.available:
            typer.secho(
                f"  [OK]      {status.name}: {status.path}", fg=typer.colors.GREEN
            )
        else:
            typer.secho(
                f"  [MISSING] {status.name}: not found on PATH",
                fg=typer.colors.RED,
            )
    return all(status.available for status in statuses)


def _check_prerequisites() -> bool:
    return _print_tool_statuses(check_tools())


@app.command()
def up(
    minimal: bool = typer.Option(
        False,
        "--minimal",
        help="Use the local MVP platform profile.",
    ),
) -> None:
    """Validate the host before bootstrapping the local platform."""
    typer.secho("KubeLaunch minimal platform", bold=True)

    if not minimal:
        typer.secho(
            "The only available profile is --minimal. Run: kube-launch up --minimal",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=2)

    if not _check_prerequisites():
        typer.echo("Install the missing tools and run this command again.", err=True)
        raise typer.Exit(code=1)

    typer.secho("Host validation passed.", fg=typer.colors.GREEN)
    typer.echo("Cluster creation is not implemented yet (Milestone 2).")
    typer.echo("No changes were made.")


@app.command()
def status() -> None:
    """Show prerequisite and implementation status."""
    typer.secho("KubeLaunch status", bold=True)
    ready = _check_prerequisites()
    typer.echo("Cluster: not managed yet (Milestone 2)")
    typer.echo("Argo CD: not managed yet (Milestone 3)")

    if not ready:
        raise typer.Exit(code=1)


@app.command()
def down() -> None:
    """Validate the host before removing the local platform."""
    typer.secho("KubeLaunch cleanup", bold=True)
    if not _check_prerequisites():
        typer.echo("Install the missing tools and run this command again.", err=True)
        raise typer.Exit(code=1)

    typer.echo("Cluster cleanup is not implemented yet (Milestone 2).")
    typer.echo("No changes were made.")
