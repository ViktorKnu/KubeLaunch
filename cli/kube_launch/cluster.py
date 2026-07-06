"""k3d cluster lifecycle operations."""

import json
import subprocess
import time
from dataclasses import dataclass

CLUSTER_NAME = "kubelaunch"
KUBE_CONTEXT = f"k3d-{CLUSTER_NAME}"
API_HOST = "127.0.0.1"
KUBECTL_REQUEST_TIMEOUT = "5s"


class ClusterCommandError(RuntimeError):
    """Raised when k3d cannot complete a cluster operation."""


@dataclass(frozen=True)
class CommandResult:
    """Relevant output from an external command."""

    returncode: int
    stdout: str
    stderr: str


def _run(command: list[str]) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as error:
        raise ClusterCommandError(f"Could not run {command[0]}: {error}") from error
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _error_message(action: str, result: CommandResult) -> str:
    details = result.stderr.strip() or result.stdout.strip() or "unknown error"
    return f"Could not {action}: {details}"


def cluster_exists(name: str = CLUSTER_NAME) -> bool:
    """Return whether k3d knows about the named cluster."""
    result = _run(["k3d", "cluster", "list", "--output", "json"])
    if result.returncode != 0:
        raise ClusterCommandError(_error_message("list k3d clusters", result))

    try:
        clusters = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ClusterCommandError("k3d returned an invalid cluster list") from error

    if not isinstance(clusters, list):
        raise ClusterCommandError("k3d returned an invalid cluster list")

    return any(cluster.get("name") == name for cluster in clusters)


def create_cluster(name: str = CLUSTER_NAME) -> None:
    """Create a small local cluster and wait for k3d to report it ready."""
    result = _run(
        [
            "k3d",
            "cluster",
            "create",
            name,
            "--api-port",
            f"{API_HOST}:0",
            "--wait",
        ]
    )
    if result.returncode != 0:
        raise ClusterCommandError(_error_message("create the k3d cluster", result))


def delete_cluster(name: str = CLUSTER_NAME) -> None:
    """Delete the named local cluster."""
    result = _run(["k3d", "cluster", "delete", name])
    if result.returncode != 0:
        raise ClusterCommandError(_error_message("delete the k3d cluster", result))


def cluster_reachable(context: str = KUBE_CONTEXT) -> bool:
    """Check the Kubernetes readiness endpoint through the cluster context."""
    result = _run(
        [
            "kubectl",
            "--context",
            context,
            f"--request-timeout={KUBECTL_REQUEST_TIMEOUT}",
            "get",
            "--raw=/readyz",
        ],
    )
    return result.returncode == 0 and result.stdout.strip() == "ok"


def wait_for_cluster(
    timeout_seconds: float = 120,
    poll_interval_seconds: float = 2,
) -> bool:
    """Poll the readiness endpoint until it succeeds or the timeout expires."""
    deadline = time.monotonic() + timeout_seconds

    while True:
        if cluster_reachable():
            return True

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False

        time.sleep(min(poll_interval_seconds, remaining))
