import subprocess

import pytest
from kube_launch.cluster import (
    ClusterCommandError,
    cluster_exists,
    cluster_reachable,
    create_cluster,
    delete_cluster,
    wait_for_cluster,
)


def completed(
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def test_cluster_exists_reads_k3d_json(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return completed('[{"name": "kubelaunch"}]')

    monkeypatch.setattr(
        "kube_launch.cluster.subprocess.run",
        fake_run,
    )

    assert cluster_exists() is True
    assert commands == [["k3d", "cluster", "list", "--output", "json"]]


def test_cluster_exists_rejects_invalid_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "kube_launch.cluster.subprocess.run",
        lambda *_args, **_kwargs: completed("not json"),
    )

    with pytest.raises(ClusterCommandError, match="invalid cluster list"):
        cluster_exists()


def test_create_cluster_uses_loopback_api_and_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return completed()

    monkeypatch.setattr("kube_launch.cluster.subprocess.run", fake_run)

    create_cluster()

    assert commands == [
        [
            "k3d",
            "cluster",
            "create",
            "kubelaunch",
            "--api-port",
            "127.0.0.1:0",
            "--wait",
        ]
    ]


def test_delete_cluster_surfaces_k3d_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "kube_launch.cluster.subprocess.run",
        lambda *_args, **_kwargs: completed(
            stderr="Docker is not running", returncode=1
        ),
    )

    with pytest.raises(ClusterCommandError, match="Docker is not running"):
        delete_cluster()


def test_cluster_reachable_uses_dedicated_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return completed(stdout="ok\n")

    monkeypatch.setattr("kube_launch.cluster.subprocess.run", fake_run)

    assert cluster_reachable() is True
    assert commands == [
        [
            "kubectl",
            "--context",
            "k3d-kubelaunch",
            "--request-timeout=5s",
            "get",
            "--raw=/readyz",
        ]
    ]


def test_wait_for_cluster_retries_until_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = iter((False, False, True))
    sleeps: list[float] = []
    monkeypatch.setattr(
        "kube_launch.cluster.cluster_reachable",
        lambda: next(attempts),
    )
    monkeypatch.setattr(
        "kube_launch.cluster.time.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    assert wait_for_cluster() is True
    assert sleeps == [2, 2]


def test_wait_for_cluster_stops_at_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("kube_launch.cluster.cluster_reachable", lambda: False)

    assert wait_for_cluster(timeout_seconds=0) is False
