from operator_app.workload import build_deployment, build_service, build_status


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


def test_build_deployment_maps_aiworkload_spec() -> None:
    deployment = build_deployment(aiworkload())
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    environment = {item["name"]: item["value"] for item in container["env"]}

    assert deployment["metadata"]["name"] == "demo"
    assert deployment["metadata"]["namespace"] == "ai-workloads"
    assert deployment["spec"]["replicas"] == 2
    assert container["image"] == "example/backend:v1"
    assert environment["OLLAMA_MODEL"] == "tinyllama"
    assert environment["OLLAMA_BASE_URL"] == "http://ollama.example:11434"


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
    assert environment["OLLAMA_BASE_URL"] == (
        "http://ollama.ollama.svc.cluster.local:11434"
    )


def test_status_records_the_observed_generation() -> None:
    assert build_status(aiworkload()) == {
        "phase": "Reconciled",
        "observedGeneration": 3,
        "deploymentName": "demo",
        "serviceName": "demo",
        "model": "tinyllama",
    }
