"""Pure Kubernetes resource builders for AIWorkload reconciliation."""

API_VERSION = "platform.kubelaunch.dev/v1alpha1"
KIND = "AIWorkload"
DEFAULT_IMAGE = "kubelaunch-backend:dev"
DEFAULT_RUNTIME_URL = "http://ollama.ollama.svc.cluster.local:11434"


def _owner_reference(resource: dict) -> list[dict]:
    metadata = resource["metadata"]
    return [
        {
            "apiVersion": API_VERSION,
            "kind": KIND,
            "name": metadata["name"],
            "uid": metadata["uid"],
            "controller": True,
            "blockOwnerDeletion": False,
        }
    ]


def _labels(name: str) -> dict[str, str]:
    return {
        "app.kubernetes.io/name": name,
        "app.kubernetes.io/part-of": "kubelaunch",
        "app.kubernetes.io/managed-by": "aiworkload-operator",
        "platform.kubelaunch.dev/aiworkload": name,
    }


def build_status(resource: dict) -> dict:
    """Build the observed status without changing the source resource."""
    metadata = resource["metadata"]
    name = metadata["name"]
    return {
        "phase": "Reconciled",
        "observedGeneration": metadata.get("generation", 0),
        "deploymentName": name,
        "serviceName": name,
        "model": resource["spec"]["model"],
    }


def build_deployment(resource: dict) -> dict:
    """Build the desired backend Deployment for an AIWorkload resource."""
    metadata = resource["metadata"]
    spec = resource["spec"]
    name = metadata["name"]
    labels = _labels(name)

    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": name,
            "namespace": metadata["namespace"],
            "labels": labels,
            "ownerReferences": _owner_reference(resource),
        },
        "spec": {
            "replicas": spec.get("replicas", 1),
            "selector": {
                "matchLabels": {"platform.kubelaunch.dev/aiworkload": name}
            },
            "template": {
                "metadata": {"labels": labels},
                "spec": {
                    "automountServiceAccountToken": False,
                    "containers": [
                        {
                            "name": "backend",
                            "image": spec.get("image", DEFAULT_IMAGE),
                            "imagePullPolicy": "IfNotPresent",
                            "env": [
                                {
                                    "name": "OLLAMA_BASE_URL",
                                    "value": spec.get(
                                        "runtimeURL", DEFAULT_RUNTIME_URL
                                    ),
                                },
                                {"name": "OLLAMA_MODEL", "value": spec["model"]},
                                {
                                    "name": "OLLAMA_TIMEOUT_SECONDS",
                                    "value": "120",
                                },
                            ],
                            "ports": [{"name": "http", "containerPort": 8000}],
                            "startupProbe": {
                                "httpGet": {"path": "/health", "port": "http"},
                                "failureThreshold": 30,
                                "periodSeconds": 2,
                            },
                            "readinessProbe": {
                                "httpGet": {"path": "/health", "port": "http"},
                                "periodSeconds": 5,
                            },
                            "livenessProbe": {
                                "httpGet": {"path": "/health", "port": "http"},
                                "periodSeconds": 15,
                            },
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "128Mi"},
                                "limits": {"cpu": "500m", "memory": "512Mi"},
                            },
                            "securityContext": {
                                "allowPrivilegeEscalation": False,
                                "capabilities": {"drop": ["ALL"]},
                            },
                        }
                    ],
                },
            },
        },
    }


def build_service(resource: dict) -> dict:
    """Build the stable Service for an AIWorkload backend."""
    metadata = resource["metadata"]
    name = metadata["name"]

    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": name,
            "namespace": metadata["namespace"],
            "labels": _labels(name),
            "ownerReferences": _owner_reference(resource),
        },
        "spec": {
            "selector": {"platform.kubelaunch.dev/aiworkload": name},
            "ports": [{"name": "http", "port": 8000, "targetPort": "http"}],
        },
    }
