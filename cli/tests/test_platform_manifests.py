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


def test_kustomization_references_existing_resources() -> None:
    app_directory = REPOSITORY_ROOT / "apps" / "platform-smoke-test"
    kustomization = load_yaml("apps/platform-smoke-test/kustomization.yaml")

    for resource in kustomization["resources"]:
        assert (app_directory / resource).is_file()


def test_service_selector_matches_deployment() -> None:
    deployment = load_yaml("apps/platform-smoke-test/deployment.yaml")
    service = load_yaml("apps/platform-smoke-test/service.yaml")

    pod_labels = deployment["spec"]["template"]["metadata"]["labels"]
    assert service["spec"]["selector"].items() <= pod_labels.items()
