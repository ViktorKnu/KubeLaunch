"""KubeLaunch CLI commands."""

import typer

from kube_launch.cluster import (
    CLUSTER_NAME,
    ClusterCommandError,
    cluster_exists,
    cluster_reachable,
    create_cluster,
    delete_cluster,
)
from kube_launch.prerequisites import REQUIRED_TOOLS, ToolStatus, check_tools

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


def _check_prerequisites(tool_names: tuple[str, ...] = REQUIRED_TOOLS) -> bool:
    return _print_tool_statuses(check_tools(tool_names))


def _print_cluster_error(error: ClusterCommandError) -> None:
    typer.secho(f"Cluster operation failed: {error}", fg=typer.colors.RED, err=True)


@app.command()
def up(
    minimal: bool = typer.Option(
        False,
        "--minimal",
        help="Use the local MVP platform profile.",
    ),
) -> None:
    """Create the local k3d cluster if it does not already exist."""
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

    try:
        if cluster_exists():
            typer.echo(
                f"Cluster '{CLUSTER_NAME}' already exists; leaving it unchanged."
            )
        else:
            typer.echo(f"Creating k3d cluster '{CLUSTER_NAME}'...")
            create_cluster()
            typer.secho(f"Cluster '{CLUSTER_NAME}' created.", fg=typer.colors.GREEN)

        if not cluster_reachable():
            typer.secho(
                "Cluster exists, but the Kubernetes API is not reachable.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=1)
    except ClusterCommandError as error:
        _print_cluster_error(error)
        raise typer.Exit(code=1) from error

    typer.secho("Kubernetes API is reachable.", fg=typer.colors.GREEN)
    typer.echo("Argo CD bootstrap is not implemented yet (Milestone 3).")


@app.command()
def status() -> None:
    """Show prerequisite and local cluster status."""
    typer.secho("KubeLaunch status", bold=True)
    statuses = check_tools()
    tools_ready = _print_tool_statuses(statuses)
    tool_statuses = {status.name: status.available for status in statuses}
    if not tool_statuses["k3d"]:
        typer.echo("Cluster: unknown (k3d is not available)")
        raise typer.Exit(code=1)

    try:
        if not cluster_exists():
            typer.echo(f"Cluster '{CLUSTER_NAME}': not found")
            raise typer.Exit(code=1)

        typer.echo(f"Cluster '{CLUSTER_NAME}': exists")
        if not tool_statuses["kubectl"]:
            typer.echo("Kubernetes API: unknown (kubectl is not available)")
            raise typer.Exit(code=1)

        reachable = cluster_reachable()
        if reachable:
            typer.secho("Kubernetes API: reachable", fg=typer.colors.GREEN)
        else:
            typer.secho("Kubernetes API: not reachable", fg=typer.colors.RED)
    except ClusterCommandError as error:
        _print_cluster_error(error)
        raise typer.Exit(code=1) from error

    typer.echo("Argo CD: not managed yet (Milestone 3)")
    if not tools_ready or not reachable:
        raise typer.Exit(code=1)


@app.command()
def down(
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Delete the cluster without asking for confirmation.",
    ),
) -> None:
    """Delete the local k3d cluster after confirmation."""
    typer.secho("KubeLaunch cleanup", bold=True)
    if not _check_prerequisites(("k3d",)):
        typer.echo("Install k3d and run this command again.", err=True)
        raise typer.Exit(code=1)

    try:
        if not cluster_exists():
            typer.echo(f"Cluster '{CLUSTER_NAME}' does not exist. Nothing to remove.")
            return

        if not yes:
            typer.confirm(
                f"Delete k3d cluster '{CLUSTER_NAME}' and everything in it?",
                abort=True,
            )

        typer.echo(f"Deleting k3d cluster '{CLUSTER_NAME}'...")
        delete_cluster()
    except ClusterCommandError as error:
        _print_cluster_error(error)
        raise typer.Exit(code=1) from error

    typer.secho(f"Cluster '{CLUSTER_NAME}' deleted.", fg=typer.colors.GREEN)
