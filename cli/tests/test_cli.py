from pathlib import Path

import pytest
from kube_launch.main import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def tools_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "kube_launch.prerequisites.which",
        lambda name: str(Path("tools") / name),
    )


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


def test_up_validates_without_changing_host(tools_available: None) -> None:
    result = runner.invoke(app, ["up", "--minimal"])

    assert result.exit_code == 0
    assert "Host validation passed." in result.stdout
    assert "No changes were made." in result.stdout


def test_status_shows_planned_components(tools_available: None) -> None:
    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert "Cluster: not managed yet (Milestone 2)" in result.stdout
    assert "Argo CD: not managed yet (Milestone 3)" in result.stdout


def test_down_is_an_explicit_no_op(tools_available: None) -> None:
    result = runner.invoke(app, ["down"])

    assert result.exit_code == 0
    assert "cleanup is not implemented yet" in result.stdout
    assert "No changes were made." in result.stdout
