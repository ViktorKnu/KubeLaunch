from operator_app.workload import (
    build_canary_deployment,
    build_deployment,
    build_service,
    build_status,
    build_status_patch,
    rollout_ready_replicas,
)


def aiworkload() -> dict:
    return {
        "apiVersion": "platform.kubelaunch.dev/v1alpha1",
        "kind": "AIWorkload",
        "metadata": {
            "name": "demo",
            "namespace": "ai-workloads",
            "uid": "workload-uid",
            "generation": 3,
        },
        "spec": {
            "model": "tinyllama",
            "image": "example/backend:v1",
            "runtimeURL": "http://ollama.example:11434",
            "replicas": 2,
        },
    }


def test_rollout_readiness_rejects_stale_and_old_replicas() -> None:
    assert rollout_ready_replicas(
        generation=4,
        observed_generation=3,
        ready_replicas=2,
        updated_replicas=2,
    ) == 0
    assert rollout_ready_replicas(
        generation=4,
        observed_generation=4,
        ready_replicas=3,
        updated_replicas=1,
    ) == 1


def test_build_deployment_maps_aiworkload_spec() -> None:
    deployment = build_deployment(aiworkload())
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    environment = {item["name"]: item["value"] for item in container["env"]}

    assert deployment["metadata"]["name"] == "demo"
    assert deployment["metadata"]["namespace"] == "ai-workloads"
    assert deployment["spec"]["replicas"] == 2
    assert container["image"] == "example/backend:v1"
    assert environment["AI_RUNTIME"] == "ollama"
    assert environment["AI_MODEL"] == "tinyllama"
    assert environment["AI_RUNTIME_BASE_URL"] == "http://ollama.example:11434"


def test_generated_resources_are_owned_by_aiworkload() -> None:
    deployment = build_deployment(aiworkload())
    service = build_service(aiworkload())
    expected_owner = {
        "apiVersion": "platform.kubelaunch.dev/v1alpha1",
        "kind": "AIWorkload",
        "name": "demo",
        "uid": "workload-uid",
        "controller": True,
        "blockOwnerDeletion": False,
    }

    assert deployment["metadata"]["ownerReferences"] == [expected_owner]
    assert service["metadata"]["ownerReferences"] == [expected_owner]


def test_service_selects_generated_deployment() -> None:
    deployment = build_deployment(aiworkload())
    service = build_service(aiworkload())

    assert service["spec"]["selector"].items() <= deployment["spec"]["template"][
        "metadata"
    ]["labels"].items()
    assert service["spec"]["selector"] == {
        "platform.kubelaunch.dev/aiworkload": "demo"
    }
    assert service["spec"]["ports"] == [
        {"name": "http", "port": 8000, "targetPort": "http"}
    ]


def test_defaults_use_local_backend_and_ollama() -> None:
    resource = aiworkload()
    resource["spec"] = {"model": "tinyllama"}
    deployment = build_deployment(resource)
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    environment = {item["name"]: item["value"] for item in container["env"]}

    assert deployment["spec"]["replicas"] == 1
    assert container["image"] == "kubelaunch-backend:dev"
    assert environment["AI_RUNTIME"] == "ollama"
    assert environment["AI_RUNTIME_BASE_URL"] == (
        "http://ollama.ollama.svc.cluster.local:11434"
    )


def test_vllm_uses_openai_compatible_service_by_default() -> None:
    resource = aiworkload()
    resource["spec"] = {
        "model": "Qwen/Qwen2.5-0.5B-Instruct",
        "runtime": "vllm",
    }
    deployment = build_deployment(resource)
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    environment = {item["name"]: item["value"] for item in container["env"]}

    assert environment["AI_RUNTIME"] == "vllm"
    assert environment["AI_RUNTIME_BASE_URL"] == (
        "http://vllm.vllm.svc.cluster.local:8000"
    )


def test_status_records_the_observed_generation() -> None:
    assert build_status(aiworkload(), stable_ready_replicas=2) == {
        "phase": "Ready",
        "observedGeneration": 3,
        "deploymentName": "demo",
        "serviceName": "demo",
        "model": "tinyllama",
        "runtime": "ollama",
        "stableReadyReplicas": 2,
        "conditions": [
            {
                "type": "StableReady",
                "status": "True",
                "reason": "MinimumReplicasAvailable",
            }
        ],
    }


def test_canary_deployment_shares_service_without_overlapping_selectors() -> None:
    resource = aiworkload()
    resource["spec"]["canary"] = {
        "model": "qwen2:0.5b",
        "replicas": 1,
    }
    stable = build_deployment(resource)
    canary = build_canary_deployment(resource)
    service = build_service(resource)

    assert canary is not None
    assert canary["metadata"]["name"] == "demo-canary"
    assert stable["spec"]["selector"] != canary["spec"]["selector"]
    for deployment in (stable, canary):
        pod_labels = deployment["spec"]["template"]["metadata"]["labels"]
        assert service["spec"]["selector"].items() <= pod_labels.items()

    container = canary["spec"]["template"]["spec"]["containers"][0]
    environment = {item["name"]: item["value"] for item in container["env"]}
    assert container["image"] == "example/backend:v1"
    assert environment["AI_MODEL"] == "qwen2:0.5b"
    assert environment["AI_RUNTIME"] == "ollama"
    assert environment["AI_RUNTIME_BASE_URL"] == "http://ollama.example:11434"


def test_canary_status_reports_replica_based_traffic_share() -> None:
    resource = aiworkload()
    resource["spec"]["canary"] = {
        "model": "qwen2:0.5b",
        "runtime": "vllm",
        "replicas": 1,
    }

    status = build_status(
        resource,
        stable_ready_replicas=2,
        canary_ready_replicas=1,
    )

    assert status["phase"] == "CanaryReady"
    assert status["canaryDeploymentName"] == "demo-canary"
    assert status["canaryModel"] == "qwen2:0.5b"
    assert status["canaryRuntime"] == "vllm"
    assert status["estimatedCanaryTrafficPercent"] == 33
    assert status["stableReadyReplicas"] == 2
    assert status["canaryReadyReplicas"] == 1
    assert [condition["status"] for condition in status["conditions"]] == [
        "True",
        "True",
    ]


def test_canary_status_stays_progressing_until_both_deployments_are_ready() -> None:
    resource = aiworkload()
    resource["spec"]["canary"] = {"model": "qwen2:0.5b", "replicas": 1}

    status = build_status(
        resource,
        stable_ready_replicas=2,
        canary_ready_replicas=0,
    )

    assert status["phase"] == "CanaryProgressing"
    assert status["conditions"][0]["status"] == "True"
    assert status["conditions"][1] == {
        "type": "CanaryReady",
        "status": "False",
        "reason": "ReplicasUnavailable",
    }


def test_status_patch_clears_removed_canary_fields() -> None:
    resource = aiworkload()
    resource["status"] = build_status(resource) | {
        "canaryDeploymentName": "demo-canary",
        "canaryModel": "old-model",
        "estimatedCanaryTrafficPercent": 33,
    }

    patch = build_status_patch(resource)

    assert patch is not None
    assert patch["phase"] == "Progressing"
    assert patch["canaryDeploymentName"] is None
    assert patch["canaryModel"] is None
    assert patch["estimatedCanaryTrafficPercent"] is None
