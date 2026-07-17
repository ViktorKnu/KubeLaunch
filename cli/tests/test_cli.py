from pathlib import Path

import pytest
from kube_launch.argocd import ApplicationStatus, ArgoCDStatus
from kube_launch.main import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def tools_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "kube_launch.prerequisites.which",
        lambda name: str(Path("tools") / name),
    )


@pytest.fixture
def argocd_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "kube_launch.main.argocd_status",
        lambda: ArgoCDStatus(True, True, 1, 1),
    )
    monkeypatch.setattr("kube_launch.main.root_application_exists", lambda: True)
    monkeypatch.setattr(
        "kube_launch.main.application_status",
        lambda _name: ApplicationStatus(True, "Synced", "Healthy"),
    )


@pytest.fixture
def bootstrap_spy(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(
        "kube_launch.main.install_argocd",
        lambda: calls.append("install"),
    )
    monkeypatch.setattr(
        "kube_launch.main.apply_root_application",
        lambda: calls.append("apply-root"),
    )
    return calls


def test_help_lists_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "up" in result.stdout
    assert "status" in result.stdout
    assert "down" in result.stdout


def test_up_requires_minimal_profile() -> None:
    result = runner.invoke(app, ["up"])

    assert result.exit_code == 2
    assert "kube-launch up --minimal" in result.output


def test_up_reports_all_missing_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("kube_launch.prerequisites.which", lambda _name: None)

    result = runner.invoke(app, ["up", "--minimal"])

    assert result.exit_code == 1
    assert "[MISSING] kubectl" in result.stdout
    assert "[MISSING] k3d" in result.stdout
    assert "[MISSING] helm" in result.stdout


def test_up_creates_cluster(
    monkeypatch: pytest.MonkeyPatch,
    tools_available: None,
    bootstrap_spy: list[str],
) -> None:
    created: list[bool] = []
    monkeypatch.setattr("kube_launch.main.cluster_exists", lambda: False)
    monkeypatch.setattr("kube_launch.main.create_cluster", lambda: created.append(True))
    monkeypatch.setattr("kube_launch.main.wait_for_cluster", lambda: True)

    result = runner.invoke(app, ["up", "--minimal"])

    assert result.exit_code == 0
    assert created == [True]
    assert bootstrap_spy == ["install", "apply-root"]
    assert "Cluster 'kubelaunch' created." in result.stdout
    assert "Kubernetes API is reachable." in result.stdout


def test_up_keeps_existing_cluster_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    tools_available: None,
    bootstrap_spy: list[str],
) -> None:
    monkeypatch.setattr("kube_launch.main.cluster_exists", lambda: True)
    monkeypatch.setattr(
        "kube_launch.main.create_cluster",
        lambda: pytest.fail("existing cluster must not be recreated"),
    )
    monkeypatch.setattr("kube_launch.main.wait_for_cluster", lambda: True)

    result = runner.invoke(app, ["up", "--minimal"])

    assert result.exit_code == 0
    assert "already exists; leaving it unchanged" in result.stdout
    assert bootstrap_spy == ["install", "apply-root"]


def test_status_reports_reachable_cluster(
    monkeypatch: pytest.MonkeyPatch,
    tools_available: None,
    argocd_ready: None,
) -> None:
    monkeypatch.setattr("kube_launch.main.cluster_exists", lambda: True)
    monkeypatch.setattr("kube_launch.main.cluster_reachable", lambda: True)

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "Cluster 'kubelaunch': exists" in result.stdout
    assert "Kubernetes API: reachable" in result.stdout
    assert "Argo CD: ready (1/1)" in result.stdout
    assert "Root Application: applied" in result.stdout
    assert "Observability: Synced / Healthy" in result.stdout
    assert "KEDA: Synced / Healthy" in result.stdout
    assert "Ollama: Synced / Healthy" in result.stdout
    assert "AI demo backend: Synced / Healthy" in result.stdout
    assert "AI demo frontend: Synced / Healthy" in result.stdout
    assert "service/ai-demo-frontend 8080:8080" in result.stdout
    assert "Frontend URL: http://localhost:8080" in result.stdout
    assert "service/kubelaunch-grafana 3000:80" in result.stdout
    assert "Grafana URL: http://localhost:3000" in result.stdout
    assert "service/ollama 11434:11434" in result.stdout


def test_status_reports_missing_cluster(
    monkeypatch: pytest.MonkeyPatch,
    tools_available: None,
) -> None:
    monkeypatch.setattr("kube_launch.main.cluster_exists", lambda: False)

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "Cluster 'kubelaunch': not found" in result.stdout


def test_status_reports_missing_argocd(
    monkeypatch: pytest.MonkeyPatch,
    tools_available: None,
) -> None:
    monkeypatch.setattr("kube_launch.main.cluster_exists", lambda: True)
    monkeypatch.setattr("kube_launch.main.cluster_reachable", lambda: True)
    monkeypatch.setattr(
        "kube_launch.main.argocd_status",
        lambda: ArgoCDStatus(False, False),
    )

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "Argo CD: not installed" in result.stdout


def test_status_reports_applications_still_syncing(
    monkeypatch: pytest.MonkeyPatch,
    tools_available: None,
) -> None:
    monkeypatch.setattr("kube_launch.main.cluster_exists", lambda: True)
    monkeypatch.setattr("kube_launch.main.cluster_reachable", lambda: True)
    monkeypatch.setattr(
        "kube_launch.main.argocd_status",
        lambda: ArgoCDStatus(True, True, 1, 1),
    )
    monkeypatch.setattr("kube_launch.main.root_application_exists", lambda: True)
    monkeypatch.setattr(
        "kube_launch.main.application_status",
        lambda _name: ApplicationStatus(True, "OutOfSync", "Progressing"),
    )

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "Observability: OutOfSync / Progressing" in result.stdout
    assert "Grafana URL: http://localhost:3000" in result.stdout


def test_status_reports_missing_application(
    monkeypatch: pytest.MonkeyPatch,
    tools_available: None,
) -> None:
    monkeypatch.setattr("kube_launch.main.cluster_exists", lambda: True)
    monkeypatch.setattr("kube_launch.main.cluster_reachable", lambda: True)
    monkeypatch.setattr(
        "kube_launch.main.argocd_status",
        lambda: ArgoCDStatus(True, True, 1, 1),
    )
    monkeypatch.setattr("kube_launch.main.root_application_exists", lambda: True)
    monkeypatch.setattr(
        "kube_launch.main.application_status",
        lambda name: (
            ApplicationStatus(False)
            if name == "ai-demo-frontend"
            else ApplicationStatus(True, "Synced", "Healthy")
        ),
    )

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "AI demo frontend: missing" in result.stdout


def test_status_stops_when_cluster_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
    tools_available: None,
) -> None:
    monkeypatch.setattr("kube_launch.main.cluster_exists", lambda: True)
    monkeypatch.setattr("kube_launch.main.cluster_reachable", lambda: False)
    monkeypatch.setattr(
        "kube_launch.main.argocd_status",
        lambda: pytest.fail("Argo CD must not be queried without a reachable API"),
    )

    result = runner.invoke(app, ["status"])

    assert result.exit_code == 1
    assert "Kubernetes API: not reachable" in result.stdout


def test_down_is_idempotent_when_cluster_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tools_available: None,
) -> None:
    monkeypatch.setattr("kube_launch.main.cluster_exists", lambda: False)

    result = runner.invoke(app, ["down"])

    assert result.exit_code == 0
    assert "Nothing to remove." in result.stdout


def test_down_deletes_cluster_with_yes_flag(
    monkeypatch: pytest.MonkeyPatch,
    tools_available: None,
) -> None:
    deleted: list[bool] = []
    monkeypatch.setattr("kube_launch.main.cluster_exists", lambda: True)
    monkeypatch.setattr("kube_launch.main.delete_cluster", lambda: deleted.append(True))

    result = runner.invoke(app, ["down", "--yes"])

    assert result.exit_code == 0
    assert deleted == [True]
    assert "Cluster 'kubelaunch' deleted." in result.stdout


def test_down_can_be_cancelled(
    monkeypatch: pytest.MonkeyPatch,
    tools_available: None,
) -> None:
    monkeypatch.setattr("kube_launch.main.cluster_exists", lambda: True)
    monkeypatch.setattr(
        "kube_launch.main.delete_cluster",
        lambda: pytest.fail("cancelled deletion must not run"),
    )

    result = runner.invoke(app, ["down"], input="n\n")

    assert result.exit_code == 1
    assert "Aborted" in result.output
