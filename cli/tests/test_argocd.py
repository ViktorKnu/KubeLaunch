import subprocess
from pathlib import Path

import pytest
import yaml
from kube_launch.argocd import (
    ARGOCD_CHART_VERSION,
    application_status,
    apply_root_application,
    argocd_status,
    install_argocd,
    root_application_exists,
)


def completed(
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def test_install_argocd_uses_pinned_chart_and_waits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return completed()

    monkeypatch.setattr("kube_launch.argocd.subprocess.run", fake_run)

    install_argocd()

    command = commands[0]
    assert command[:5] == ["helm", "upgrade", "--install", "argocd", "argo-cd"]
    assert command[command.index("--version") + 1] == ARGOCD_CHART_VERSION
    assert "--wait" in command
    assert command[command.index("--kube-context") + 1] == "k3d-kubelaunch"


def test_apply_root_application_uses_cluster_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "root.yaml"
    manifest.write_text("kind: Application\n", encoding="utf-8")
    commands: list[list[str]] = []

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return completed()

    monkeypatch.setattr("kube_launch.argocd.subprocess.run", fake_run)

    apply_root_application(manifest)

    assert commands == [
        [
            "kubectl",
            "--context",
            "k3d-kubelaunch",
            "apply",
            "--filename",
            str(manifest),
        ]
    ]


def test_argocd_status_reads_ready_replicas(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = '{"spec":{"replicas":1},"status":{"readyReplicas":1}}'
    monkeypatch.setattr(
        "kube_launch.argocd.subprocess.run",
        lambda *_args, **_kwargs: completed(stdout=payload),
    )

    status = argocd_status()

    assert status.installed is True
    assert status.ready is True
    assert status.ready_replicas == 1


def test_argocd_status_handles_missing_deployment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    not_found = 'Error from server (NotFound): deployment "argocd-server" not found'
    monkeypatch.setattr(
        "kube_launch.argocd.subprocess.run",
        lambda *_args, **_kwargs: completed(
            stderr=not_found,
            returncode=1,
        ),
    )

    status = argocd_status()

    assert status.installed is False
    assert status.ready is False


def test_root_application_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "kube_launch.argocd.subprocess.run",
        lambda *_args, **_kwargs: completed(
            stdout="application.argoproj.io/kubelaunch"
        ),
    )

    assert root_application_exists() is True


def test_application_status_reads_sync_and_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = '{"status":{"sync":{"status":"Synced"},"health":{"status":"Healthy"}}}'
    monkeypatch.setattr(
        "kube_launch.argocd.subprocess.run",
        lambda *_args, **_kwargs: completed(stdout=payload),
    )

    status = application_status("observability")

    assert status.exists is True
    assert status.sync_status == "Synced"
    assert status.health_status == "Healthy"


def test_application_status_handles_missing_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    not_found = 'Error from server (NotFound): Application "observability" not found'
    monkeypatch.setattr(
        "kube_launch.argocd.subprocess.run",
        lambda *_args, **_kwargs: completed(
            stderr=not_found,
            returncode=1,
        ),
    )

    status = application_status("observability")

    assert status.exists is False


def test_root_application_points_to_platform_directory() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    manifest = yaml.safe_load(
        (repository_root / "platform" / "root-application.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["kind"] == "Application"
    assert manifest["metadata"]["namespace"] == "argocd"
    assert manifest["spec"]["source"] == {
        "repoURL": "https://github.com/ViktorKnu/KubeLaunch.git",
        "targetRevision": "main",
        "path": "platform",
        "directory": {"recurse": True},
    }
