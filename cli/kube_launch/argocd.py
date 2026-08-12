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
DEFAULT_REPOSITORY_URL = "https://github.com/ViktorKnu/KubeLaunch.git"
ROOT_APPLICATION_PATHS = {
    "minimal": Path("platform") / "root-application.yaml",
    "full": Path("profiles") / "full" / "root-application.yaml",
}


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


def _run(command: list[str], *, input_text: str | None = None) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            input=input_text,
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


def install_argocd(context: str = KUBE_CONTEXT) -> None:
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
            context,
            "--wait",
            "--timeout",
            "5m",
        ]
    )
    if result.returncode != 0:
        _raise_command_error("install Argo CD", result)


def find_root_application(profile: str = "minimal") -> Path:
    """Find the root Application manifest in a source or editable install."""
    try:
        relative_path = ROOT_APPLICATION_PATHS[profile]
    except KeyError as error:
        raise ArgoCDCommandError(f"Unknown platform profile: {profile}") from error

    candidates = (
        Path.cwd() / relative_path,
        Path(__file__).resolve().parents[2] / relative_path,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise ArgoCDCommandError(
        f"Could not find {relative_path.as_posix()}. "
        "Run kube-launch from the repository root."
    )


def _git_source_patch(repository_url: str, revision: str) -> str:
    return "\n".join(
        (
            "- op: replace",
            "  path: /spec/source/repoURL",
            f"  value: {json.dumps(repository_url)}",
            "- op: replace",
            "  path: /spec/source/targetRevision",
            f"  value: {json.dumps(revision)}",
        )
    )


def _application_kustomize_patch(name: str, configuration: dict) -> dict:
    patch = "\n".join(
        (
            "- op: add",
            "  path: /spec/source/kustomize",
            f"  value: {json.dumps(configuration)}",
        )
    )
    return {
        "target": {"kind": "Application", "name": name},
        "patch": patch,
    }


def _image_override(source_image: str, target_image: str) -> dict:
    return {"images": [f"{source_image}={target_image}"]}


def _aiworkload_image_override(target_image: str) -> dict:
    patch = "\n".join(
        (
            "- op: replace",
            "  path: /spec/image",
            f"  value: {json.dumps(target_image)}",
        )
    )
    return {
        "patches": [
            {
                "target": {"kind": "AIWorkload"},
                "patch": patch,
            }
        ]
    }


def _cloud_ingress_patches(
    hostname: str,
    ingress_class: str,
    cluster_issuer: str,
) -> list[dict]:
    return [
        {
            "target": {"kind": "Ingress", "name": "kubelaunch-frontend"},
            "patch": "\n".join(
                (
                    "- op: replace",
                    "  path: /spec/ingressClassName",
                    f"  value: {json.dumps(ingress_class)}",
                    "- op: replace",
                    "  path: /spec/rules/0/host",
                    f"  value: {json.dumps(hostname)}",
                    "- op: replace",
                    "  path: /spec/tls/0/hosts/0",
                    f"  value: {json.dumps(hostname)}",
                )
            ),
        },
        {
            "target": {"kind": "Certificate", "name": "kubelaunch-frontend"},
            "patch": "\n".join(
                (
                    "- op: replace",
                    "  path: /spec/dnsNames/0",
                    f"  value: {json.dumps(hostname)}",
                    "- op: replace",
                    "  path: /spec/issuerRef/name",
                    f"  value: {json.dumps(cluster_issuer)}",
                )
            ),
        },
    ]


def build_root_application(
    profile: str,
    repository_url: str,
    revision: str,
    backend_image: str,
    frontend_image: str,
    operator_image: str | None = None,
    ingress_hostname: str | None = None,
    ingress_class: str | None = None,
    cluster_issuer: str | None = None,
) -> dict:
    """Build a root Application that propagates its Git source to child apps."""
    if profile not in ROOT_APPLICATION_PATHS:
        raise ArgoCDCommandError(f"Unknown platform profile: {profile}")

    repository_patch = {
        "target": {
            "kind": "Application",
            "labelSelector": "kubelaunch.dev/source=git",
        },
        "patch": _git_source_patch(repository_url, revision),
    }
    platform_patches = [
        repository_patch,
        _application_kustomize_patch(
            "ai-demo-backend",
            _image_override("kubelaunch-backend:dev", backend_image),
        ),
        _application_kustomize_patch(
            "ai-demo-frontend",
            _image_override("kubelaunch-frontend:dev", frontend_image),
        ),
    ]
    sources = [
        {
            "repoURL": repository_url,
            "targetRevision": revision,
            "path": "platform/components",
            "kustomize": {"patches": platform_patches},
        }
    ]
    if profile == "full":
        if not operator_image:
            raise ArgoCDCommandError("The full profile requires an operator image")
        sources.append(
            {
                "repoURL": repository_url,
                "targetRevision": revision,
                "path": "profiles/full/components",
                "kustomize": {
                    "patches": [
                        repository_patch,
                        _application_kustomize_patch(
                            "aiworkload-operator",
                            _image_override(
                                "kubelaunch-aiworkload-operator:dev",
                                operator_image,
                            ),
                        ),
                        _application_kustomize_patch(
                            "aiworkload-smoke-test",
                            _aiworkload_image_override(backend_image),
                        ),
                    ]
                },
            }
        )
    if ingress_hostname:
        if not ingress_class or not cluster_issuer:
            raise ArgoCDCommandError(
                "Ingress requires a class and ClusterIssuer"
            )
        sources.append(
            {
                "repoURL": repository_url,
                "targetRevision": revision,
                "path": "profiles/cloud/frontend-ingress",
                "kustomize": {
                    "patches": _cloud_ingress_patches(
                        ingress_hostname,
                        ingress_class,
                        cluster_issuer,
                    )
                },
            }
        )
    source_spec = (
        {"source": sources[0]}
        if profile == "minimal" and not ingress_hostname
        else {"sources": sources}
    )

    return {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Application",
        "metadata": {
            "name": ROOT_APPLICATION_NAME,
            "namespace": ARGOCD_NAMESPACE,
            "annotations": {"kubelaunch.dev/profile": profile},
            "finalizers": ["resources-finalizer.argocd.argoproj.io"],
        },
        "spec": {
            "project": "default",
            **source_spec,
            "destination": {
                "server": "https://kubernetes.default.svc",
                "namespace": ARGOCD_NAMESPACE,
            },
            "syncPolicy": {
                "automated": {"prune": True, "selfHeal": True},
            },
        },
    }


def apply_root_application(
    manifest: Path | None = None,
    profile: str = "minimal",
    context: str = KUBE_CONTEXT,
    repository_url: str | None = None,
    revision: str = "main",
    backend_image: str | None = None,
    frontend_image: str | None = None,
    operator_image: str | None = None,
    ingress_hostname: str | None = None,
    ingress_class: str | None = None,
    cluster_issuer: str | None = None,
) -> None:
    """Apply the single root Application after the Argo CD CRD is ready."""
    if manifest is not None and repository_url is not None:
        raise ArgoCDCommandError("Manifest and repository override cannot be combined")

    input_text = None
    if repository_url is None:
        manifest = manifest or find_root_application(profile)
        filename = str(manifest)
    else:
        if not backend_image or not frontend_image:
            raise ArgoCDCommandError(
                "Repository overrides require backend and frontend images"
            )
        filename = "-"
        input_text = json.dumps(
            build_root_application(
                profile,
                repository_url,
                revision,
                backend_image,
                frontend_image,
                operator_image,
                ingress_hostname,
                ingress_class,
                cluster_issuer,
            )
        )
    result = _run(
        [
            "kubectl",
            "--context",
            context,
            "apply",
            "--filename",
            filename,
        ],
        input_text=input_text,
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


def root_application_profile() -> str:
    """Return the profile annotation from the root Application."""
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
            "json",
        ]
    )
    if result.returncode != 0:
        _raise_command_error("read the root Argo CD profile", result)

    try:
        application = json.loads(result.stdout)
        profile = application.get("metadata", {}).get("annotations", {}).get(
            "kubelaunch.dev/profile", "minimal"
        )
    except (AttributeError, json.JSONDecodeError) as error:
        raise ArgoCDCommandError(
            "kubectl returned an invalid root Application profile"
        ) from error

    return str(profile)


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
