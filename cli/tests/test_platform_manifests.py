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


def test_ollama_application_points_to_local_runtime() -> None:
    application = load_yaml("platform/components/ollama-application.yaml")

    assert application["spec"]["source"]["path"] == "apps/ollama"
    assert application["spec"]["destination"]["namespace"] == "ollama"
    assert application["spec"]["syncPolicy"]["automated"] == {
        "prune": True,
        "selfHeal": True,
    }


def test_ollama_is_one_persistent_cpu_runtime() -> None:
    deployment = load_yaml("apps/ollama/deployment.yaml")
    claim = load_yaml("apps/ollama/persistent-volume-claim.yaml")
    container = deployment["spec"]["template"]["spec"]["containers"][0]

    assert deployment["spec"]["replicas"] == 1
    assert deployment["spec"]["strategy"]["type"] == "Recreate"
    assert container["image"] == "ollama/ollama:0.31.1"
    assert container["resources"]["requests"]["memory"] == "768Mi"
    assert container["volumeMounts"] == [
        {"name": "models", "mountPath": "/root/.ollama"}
    ]
    assert claim["spec"]["resources"]["requests"]["storage"] == "3Gi"


def test_ollama_model_pull_is_post_sync_hook() -> None:
    job = load_yaml("apps/ollama/model-pull-job.yaml")
    annotations = job["metadata"]["annotations"]
    container = job["spec"]["template"]["spec"]["containers"][0]

    assert annotations["argocd.argoproj.io/hook"] == "PostSync"
    assert container["image"] == "ollama/ollama:0.31.1"
    assert container["args"] == ["pull", "tinyllama"]
    assert container["env"] == [{"name": "OLLAMA_HOST", "value": "http://ollama:11434"}]


def test_ai_backend_application_uses_gitops_manifests() -> None:
    application = load_yaml("platform/components/ai-demo-backend-application.yaml")

    assert application["spec"]["source"]["path"] == "apps/ai-demo/backend/k8s"
    assert application["spec"]["destination"]["namespace"] == "ai-demo"
    assert application["metadata"]["annotations"]["argocd.argoproj.io/sync-wave"] == "2"


def test_ai_backend_connects_to_ollama_without_keda() -> None:
    directory = REPOSITORY_ROOT / "apps" / "ai-demo" / "backend" / "k8s"
    deployment = load_yaml("apps/ai-demo/backend/k8s/deployment.yaml")
    kustomization = load_yaml("apps/ai-demo/backend/k8s/kustomization.yaml")
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    environment = {item["name"]: item["value"] for item in container["env"]}

    assert deployment["spec"]["replicas"] == 1
    assert container["image"] == "kubelaunch-backend:dev"
    assert environment["OLLAMA_BASE_URL"] == (
        "http://ollama.ollama.svc.cluster.local:11434"
    )
    assert "scaled-object.yaml" not in kustomization["resources"]
    for resource in kustomization["resources"]:
        assert (directory / resource).is_file()


def test_ai_backend_metrics_are_selected_by_prometheus() -> None:
    service = load_yaml("apps/ai-demo/backend/k8s/service.yaml")
    monitor = load_yaml("apps/ai-demo/backend/k8s/service-monitor.yaml")
    selector = monitor["spec"]["selector"]["matchLabels"]

    assert monitor["metadata"]["labels"]["release"] == "observability"
    assert selector.items() <= service["metadata"]["labels"].items()
    assert monitor["spec"]["endpoints"][0]["path"] == "/metrics"


def test_kustomization_references_existing_resources() -> None:
    for app_name in ("platform-smoke-test", "keda-smoke-test", "ollama"):
        app_directory = REPOSITORY_ROOT / "apps" / app_name
        kustomization = load_yaml(f"apps/{app_name}/kustomization.yaml")

        for resource in kustomization["resources"]:
            assert (app_directory / resource).is_file()


def test_service_selector_matches_deployment() -> None:
    for app_name in ("platform-smoke-test", "keda-smoke-test", "ollama"):
        deployment = load_yaml(f"apps/{app_name}/deployment.yaml")
        service = load_yaml(f"apps/{app_name}/service.yaml")

        pod_labels = deployment["spec"]["template"]["metadata"]["labels"]
        assert service["spec"]["selector"].items() <= pod_labels.items()
