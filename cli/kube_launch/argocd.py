"""Argo CD bootstrap and status operations."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from kube_launch.cluster import KUBE_CONTEXT

ARGOCD_NAMESPACE = "argocd"
ARGOCD_RELEASE = "argocd"
ARGOCD_CHART = "argo-cd"
ARGOCD_CHART_REPOSITORY = "https://argoproj.github.io/argo-helm"
ARGOCD_CHART_VERSION = "9.5.17"
ROOT_APPLICATION_NAME = "kubelaunch"


class ArgoCDCommandError(RuntimeError):
    """Raised when Argo CD bootstrap or inspection fails."""


@dataclass(frozen=True)
class CommandResult:
    """Relevant output from an external command."""

    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class ArgoCDStatus:
    """Readiness information for the Argo CD server deployment."""

    installed: bool
    ready: bool
    ready_replicas: int = 0
    desired_replicas: int = 0


@dataclass(frozen=True)
class ApplicationStatus:
    """Sync and health information for an Argo CD Application."""

    exists: bool
    sync_status: str = "Unknown"
    health_status: str = "Unknown"


def _run(command: list[str]) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as error:
        raise ArgoCDCommandError(f"Could not run {command[0]}: {error}") from error

    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _raise_command_error(action: str, result: CommandResult) -> None:
    details = result.stderr.strip() or result.stdout.strip() or "unknown error"
    raise ArgoCDCommandError(f"Could not {action}: {details}")


def install_argocd() -> None:
    """Install or update Argo CD and wait for the Helm release to be ready."""
    result = _run(
        [
            "helm",
            "upgrade",
            "--install",
            ARGOCD_RELEASE,
            ARGOCD_CHART,
            "--repo",
            ARGOCD_CHART_REPOSITORY,
            "--version",
            ARGOCD_CHART_VERSION,
            "--namespace",
            ARGOCD_NAMESPACE,
            "--create-namespace",
            "--kube-context",
            KUBE_CONTEXT,
            "--wait",
            "--timeout",
            "5m",
        ]
    )
    if result.returncode != 0:
        _raise_command_error("install Argo CD", result)


def find_root_application() -> Path:
    """Find the root Application manifest in a source or editable install."""
    candidates = (
        Path.cwd() / "platform" / "root-application.yaml",
        Path(__file__).resolve().parents[2] / "platform" / "root-application.yaml",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise ArgoCDCommandError(
        "Could not find platform/root-application.yaml. "
        "Run kube-launch from the repository root."
    )


def apply_root_application(manifest: Path | None = None) -> None:
    """Apply the single root Application after the Argo CD CRD is ready."""
    manifest = manifest or find_root_application()
    result = _run(
        [
            "kubectl",
            "--context",
            KUBE_CONTEXT,
            "apply",
            "--filename",
            str(manifest),
        ]
    )
    if result.returncode != 0:
        _raise_command_error("apply the root Argo CD Application", result)


def argocd_status() -> ArgoCDStatus:
    """Return the readiness of the Argo CD server deployment."""
    result = _run(
        [
            "kubectl",
            "--context",
            KUBE_CONTEXT,
            "--namespace",
            ARGOCD_NAMESPACE,
            "get",
            "deployment",
            "argocd-server",
            "--output",
            "json",
        ]
    )
    if result.returncode != 0:
        if "notfound" in result.stderr.replace(" ", "").lower():
            return ArgoCDStatus(installed=False, ready=False)
        _raise_command_error("read Argo CD status", result)

    try:
        deployment = json.loads(result.stdout)
        desired = int(deployment.get("spec", {}).get("replicas", 1))
        ready = int(deployment.get("status", {}).get("readyReplicas", 0))
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ArgoCDCommandError(
            "kubectl returned an invalid Argo CD status"
        ) from error

    return ArgoCDStatus(
        installed=True,
        ready=desired > 0 and ready >= desired,
        ready_replicas=ready,
        desired_replicas=desired,
    )


def root_application_exists() -> bool:
    """Return whether the root Application is present in the cluster."""
    result = _run(
        [
            "kubectl",
            "--context",
            KUBE_CONTEXT,
            "--namespace",
            ARGOCD_NAMESPACE,
            "get",
            "application",
            ROOT_APPLICATION_NAME,
            "--output",
            "name",
        ]
    )
    if result.returncode == 0:
        return True
    if "notfound" in result.stderr.replace(" ", "").lower():
        return False
    _raise_command_error("read the root Argo CD Application", result)


def application_status(name: str) -> ApplicationStatus:
    """Return Argo CD sync and health status for an Application."""
    result = _run(
        [
            "kubectl",
            "--context",
            KUBE_CONTEXT,
            "--namespace",
            ARGOCD_NAMESPACE,
            "get",
            "application",
            name,
            "--output",
            "json",
        ]
    )
    if result.returncode != 0:
        if "notfound" in result.stderr.replace(" ", "").lower():
            return ApplicationStatus(exists=False)
        _raise_command_error(f"read Argo CD Application '{name}'", result)

    try:
        application = json.loads(result.stdout)
        sync_status = (
            application.get("status", {}).get("sync", {}).get("status", "Unknown")
        )
        health_status = (
            application.get("status", {}).get("health", {}).get("status", "Unknown")
        )
    except (AttributeError, json.JSONDecodeError) as error:
        raise ArgoCDCommandError(
            f"kubectl returned an invalid status for Application '{name}'"
        ) from error

    return ApplicationStatus(
        exists=True,
        sync_status=str(sync_status),
        health_status=str(health_status),
    )
