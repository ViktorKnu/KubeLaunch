from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def load_yaml(relative_path: str) -> dict:
    return yaml.safe_load((REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8"))


def test_root_application_recursively_loads_platform() -> None:
    root = load_yaml("platform/root-application.yaml")

    assert root["spec"]["source"]["path"] == "platform"
    assert root["spec"]["source"]["directory"]["recurse"] is True


def test_smoke_test_application_uses_kustomize_directory() -> None:
    application = load_yaml("platform/components/smoke-test-application.yaml")

    assert application["kind"] == "Application"
    assert application["metadata"]["namespace"] == "argocd"
    assert application["spec"]["source"]["path"] == "apps/platform-smoke-test"
    assert application["spec"]["destination"]["namespace"] == "kubelaunch-system"
    assert "CreateNamespace=true" in application["spec"]["syncPolicy"]["syncOptions"]


def test_observability_uses_pinned_prometheus_stack() -> None:
    application = load_yaml("platform/components/observability-application.yaml")
    source = application["spec"]["source"]
    values = source["helm"]["valuesObject"]

    assert source["chart"] == "kube-prometheus-stack"
    assert source["targetRevision"] == "86.0.0"
    assert application["spec"]["destination"]["namespace"] == "monitoring"
    assert values["alertmanager"]["enabled"] is False
    assert values["grafana"]["enabled"] is True
    assert values["grafana"]["fullnameOverride"] == "kubelaunch-grafana"
    assert values["prometheus"]["prometheusSpec"]["retention"] == "6h"
    assert "ServerSideApply=true" in application["spec"]["syncPolicy"]["syncOptions"]


def test_keda_uses_pinned_official_chart() -> None:
    application = load_yaml("platform/components/keda-application.yaml")
    source = application["spec"]["source"]

    assert source["repoURL"] == "https://kedacore.github.io/charts"
    assert source["chart"] == "keda"
    assert source["targetRevision"] == "2.20.1"
    assert application["spec"]["destination"]["namespace"] == "keda"
    assert application["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "0"


def test_keda_smoke_test_waits_for_keda_and_ignores_replicas() -> None:
    application = load_yaml("platform/components/keda-smoke-test-application.yaml")

    assert application["spec"]["source"]["path"] == "apps/keda-smoke-test"
    assert application["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "1"
    assert application["spec"]["ignoreDifferences"][0]["jsonPointers"] == [
        "/spec/replicas"
    ]
    assert (
        "RespectIgnoreDifferences=true"
        in application["spec"]["syncPolicy"]["syncOptions"]
    )


def test_keda_scaled_object_targets_cpu_workload() -> None:
    scaled_object = load_yaml("apps/keda-smoke-test/scaled-object.yaml")
    deployment = load_yaml("apps/keda-smoke-test/deployment.yaml")
    trigger = scaled_object["spec"]["triggers"][0]

    assert scaled_object["spec"]["scaleTargetRef"]["name"] == "keda-smoke-test"
    assert scaled_object["spec"]["minReplicaCount"] == 1
    assert scaled_object["spec"]["maxReplicaCount"] == 3
    assert trigger == {
        "type": "cpu",
        "metricType": "Utilization",
        "metadata": {"value": "50"},
    }
    assert (
        deployment["spec"]["template"]["spec"]["containers"][0]["resources"][
            "requests"
        ]["cpu"]
        == "200m"
    )


def test_kustomization_references_existing_resources() -> None:
    for app_name in ("platform-smoke-test", "keda-smoke-test"):
        app_directory = REPOSITORY_ROOT / "apps" / app_name
        kustomization = load_yaml(f"apps/{app_name}/kustomization.yaml")

        for resource in kustomization["resources"]:
            assert (app_directory / resource).is_file()


def test_service_selector_matches_deployment() -> None:
    deployment = load_yaml("apps/platform-smoke-test/deployment.yaml")
    service = load_yaml("apps/platform-smoke-test/service.yaml")

    pod_labels = deployment["spec"]["template"]["metadata"]["labels"]
    assert service["spec"]["selector"].items() <= pod_labels.items()
