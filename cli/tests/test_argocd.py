import json
import subprocess
from pathlib import Path

import pytest
import yaml
from kube_launch.argocd import (
    ARGOCD_CHART_VERSION,
    application_status,
    apply_root_application,
    argocd_status,
    build_root_application,
    install_argocd,
    root_application_exists,
    root_application_profile,
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

    install_argocd(context="aks-team")

    command = commands[0]
    assert command[:5] == ["helm", "upgrade", "--install", "argocd", "argo-cd"]
    assert command[command.index("--version") + 1] == ARGOCD_CHART_VERSION
    assert "--wait" in command
    assert command[command.index("--kube-context") + 1] == "aks-team"


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


def test_apply_root_application_renders_repository_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["input"] = kwargs["input"]
        return completed()

    monkeypatch.setattr("kube_launch.argocd.subprocess.run", fake_run)

    apply_root_application(
        profile="minimal",
        context="aks-team",
        repository_url="https://github.com/example/fork.git",
        revision="release-1",
        backend_image="registry.example/backend:release-1",
        frontend_image="registry.example/frontend:release-1",
    )

    assert captured["command"] == [
        "kubectl",
        "--context",
        "aks-team",
        "apply",
        "--filename",
        "-",
    ]
    application = json.loads(str(captured["input"]))
    source = application["spec"]["source"]
    assert source["repoURL"] == "https://github.com/example/fork.git"
    assert source["targetRevision"] == "release-1"
    assert source["path"] == "platform/components"
    patch = source["kustomize"]["patches"][0]
    assert patch["target"]["labelSelector"] == "kubelaunch.dev/source=git"
    assert "https://github.com/example/fork.git" in patch["patch"]
    assert "release-1" in patch["patch"]
    image_patches = source["kustomize"]["patches"]
    assert "registry.example/backend:release-1" in image_patches[1]["patch"]
    assert "registry.example/frontend:release-1" in image_patches[2]["patch"]


def test_full_root_builder_uses_both_component_directories() -> None:
    application = build_root_application(
        "full",
        "https://github.com/example/fork.git",
        "main",
        "registry.example/backend:v1",
        "registry.example/frontend:v1",
        "registry.example/operator:v1",
    )

    assert [source["path"] for source in application["spec"]["sources"]] == [
        "platform/components",
        "profiles/full/components",
    ]
    full_patches = application["spec"]["sources"][1]["kustomize"]["patches"]
    assert "registry.example/operator:v1" in full_patches[1]["patch"]
    assert "registry.example/backend:v1" in full_patches[2]["patch"]


def test_root_builder_adds_configured_tls_ingress_source() -> None:
    application = build_root_application(
        "minimal",
        "https://github.com/example/fork.git",
        "main",
        "registry.example/backend:v1",
        "registry.example/frontend:v1",
        ingress_hostname="ai.example.com",
        ingress_class="gce",
        cluster_issuer="letsencrypt-production",
    )

    ingress_source = application["spec"]["sources"][1]
    assert ingress_source["path"] == "profiles/cloud/frontend-ingress"
    patches = ingress_source["kustomize"]["patches"]
    assert "ai.example.com" in patches[0]["patch"]
    assert "gce" in patches[0]["patch"]
    assert "letsencrypt-production" in patches[1]["patch"]


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


def test_root_application_profile_reads_annotation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = '{"metadata":{"annotations":{"kubelaunch.dev/profile":"full"}}}'
    monkeypatch.setattr(
        "kube_launch.argocd.subprocess.run",
        lambda *_args, **_kwargs: completed(stdout=payload),
    )

    assert root_application_profile() == "full"


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
    assert manifest["metadata"]["annotations"]["kubelaunch.dev/profile"] == "minimal"
    assert manifest["spec"]["source"] == {
        "repoURL": "https://github.com/ViktorKnu/KubeLaunch.git",
        "targetRevision": "main",
        "path": "platform/components",
    }


def test_full_root_application_combines_common_and_full_components() -> None:
    repository_root = Path(__file__).resolve().parents[2]
    manifest = yaml.safe_load(
        (repository_root / "profiles" / "full" / "root-application.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["metadata"]["annotations"]["kubelaunch.dev/profile"] == "full"
    assert [source["path"] for source in manifest["spec"]["sources"]] == [
        "platform/components",
        "profiles/full/components",
    ]
