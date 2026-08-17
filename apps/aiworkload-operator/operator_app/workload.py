"""Pure Kubernetes resource builders for AIWorkload reconciliation."""

import json

API_VERSION = "platform.kubelaunch.dev/v1alpha1"
KIND = "AIWorkload"
DEFAULT_IMAGE = "kubelaunch-backend:dev"
DEFAULT_RUNTIME = "ollama"
DEFAULT_RUNTIME_URLS = {
    "ollama": "http://ollama.ollama.svc.cluster.local:11434",
    "vllm": "http://vllm.vllm.svc.cluster.local:8000",
}


def rollout_ready_replicas(
    *,
    generation: int,
    observed_generation: int,
    ready_replicas: int,
    updated_replicas: int,
) -> int:
    """Count ready replicas only after the latest rollout is observed."""
    if observed_generation < generation:
        return 0
    return min(ready_replicas, updated_replicas)


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
        "platform.kubelaunch.dev/traffic-group": name,
    }


def _canary_labels(name: str) -> dict[str, str]:
    return {
        "app.kubernetes.io/name": f"{name}-canary",
        "app.kubernetes.io/part-of": "kubelaunch",
        "app.kubernetes.io/managed-by": "aiworkload-operator",
        "platform.kubelaunch.dev/aiworkload-canary": name,
        "platform.kubelaunch.dev/traffic-group": name,
    }


def _ready_condition(name: str, ready: bool) -> dict[str, str]:
    return {
        "type": name,
        "status": "True" if ready else "False",
        "reason": "MinimumReplicasAvailable" if ready else "ReplicasUnavailable",
    }


def build_status(
    resource: dict,
    stable_ready_replicas: int = 0,
    canary_ready_replicas: int = 0,
) -> dict:
    """Build readiness analysis without changing the source resource."""
    metadata = resource["metadata"]
    name = metadata["name"]
    stable_replicas = resource["spec"].get("replicas", 1)
    stable_ready = stable_ready_replicas >= stable_replicas
    status = {
        "phase": "Ready" if stable_ready else "Progressing",
        "observedGeneration": metadata.get("generation", 0),
        "deploymentName": name,
        "serviceName": name,
        "model": resource["spec"]["model"],
        "runtime": resource["spec"].get("runtime", DEFAULT_RUNTIME),
        "stableReadyReplicas": stable_ready_replicas,
        "conditions": [_ready_condition("StableReady", stable_ready)],
    }
    canary = resource["spec"].get("canary")
    if canary:
        canary_replicas = canary.get("replicas", 1)
        canary_ready = canary_ready_replicas >= canary_replicas
        status.update(
            {
                "phase": (
                    "CanaryReady"
                    if stable_ready and canary_ready
                    else "CanaryProgressing"
                ),
                "canaryDeploymentName": f"{name}-canary",
                "canaryModel": canary["model"],
                "canaryRuntime": canary.get(
                    "runtime", resource["spec"].get("runtime", DEFAULT_RUNTIME)
                ),
                "estimatedCanaryTrafficPercent": round(
                    canary_replicas
                    / (stable_replicas + canary_replicas)
                    * 100
                ),
                "canaryReadyReplicas": canary_ready_replicas,
            }
        )
        if canary.get("analysis", {}).get("enabled", True):
            status["analysisRuleName"] = f"{name}-canary"
        status["conditions"].append(
            _ready_condition("CanaryReady", canary_ready)
        )
    return status


def build_status_patch(
    resource: dict,
    stable_ready_replicas: int = 0,
    canary_ready_replicas: int = 0,
) -> dict | None:
    """Build an idempotent status patch and clear fields from an old canary."""
    desired_status = build_status(
        resource,
        stable_ready_replicas,
        canary_ready_replicas,
    )
    current_status = resource.get("status", {})
    if current_status == desired_status:
        return None
    return desired_status | {
        key: None for key in current_status.keys() - desired_status.keys()
    }


def _build_backend_deployment(
    resource: dict,
    *,
    name: str,
    labels: dict[str, str],
    selector: dict[str, str],
    replicas: int,
    image: str,
    runtime: str,
    runtime_url: str,
    model: str,
    track: str,
) -> dict:
    metadata = resource["metadata"]

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
            "replicas": replicas,
            "selector": {"matchLabels": selector},
            "template": {
                "metadata": {"labels": labels},
                "spec": {
                    "automountServiceAccountToken": False,
                    "containers": [
                        {
                            "name": "backend",
                            "image": image,
                            "imagePullPolicy": "IfNotPresent",
                            "env": [
                                {
                                    "name": "AI_RUNTIME",
                                    "value": runtime,
                                },
                                {
                                    "name": "AI_RUNTIME_BASE_URL",
                                    "value": runtime_url,
                                },
                                {"name": "AI_MODEL", "value": model},
                                {"name": "AI_TRACK", "value": track},
                                {
                                    "name": "AI_TIMEOUT_SECONDS",
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


def build_deployment(resource: dict) -> dict:
    """Build the desired stable backend Deployment for an AIWorkload."""
    metadata = resource["metadata"]
    spec = resource["spec"]
    name = metadata["name"]
    runtime = spec.get("runtime", DEFAULT_RUNTIME)
    return _build_backend_deployment(
        resource,
        name=name,
        labels=_labels(name),
        selector={"platform.kubelaunch.dev/aiworkload": name},
        replicas=spec.get("replicas", 1),
        image=spec.get("image", DEFAULT_IMAGE),
        runtime=runtime,
        runtime_url=spec.get("runtimeURL", DEFAULT_RUNTIME_URLS[runtime]),
        model=spec["model"],
        track="stable",
    )


def build_canary_deployment(resource: dict) -> dict | None:
    """Build the optional canary Deployment with a non-overlapping selector."""
    metadata = resource["metadata"]
    spec = resource["spec"]
    canary = spec.get("canary")
    if not canary:
        return None

    name = metadata["name"]
    stable_runtime = spec.get("runtime", DEFAULT_RUNTIME)
    runtime = canary.get("runtime", stable_runtime)
    runtime_url = canary.get("runtimeURL")
    if runtime_url is None and runtime == stable_runtime:
        runtime_url = spec.get("runtimeURL")
    if runtime_url is None:
        runtime_url = DEFAULT_RUNTIME_URLS[runtime]

    return _build_backend_deployment(
        resource,
        name=f"{name}-canary",
        labels=_canary_labels(name),
        selector={"platform.kubelaunch.dev/aiworkload-canary": name},
        replicas=canary.get("replicas", 1),
        image=canary.get("image", spec.get("image", DEFAULT_IMAGE)),
        runtime=runtime,
        runtime_url=runtime_url,
        model=canary["model"],
        track="canary",
    )


def build_service(resource: dict) -> dict:
    """Build the stable Service for an AIWorkload backend."""
    metadata = resource["metadata"]
    name = metadata["name"]
    selector_label = (
        "platform.kubelaunch.dev/traffic-group"
        if resource["spec"].get("canary")
        else "platform.kubelaunch.dev/aiworkload"
    )

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
            "selector": {selector_label: name},
            "ports": [{"name": "http", "port": 8000, "targetPort": "http"}],
        },
    }


def build_service_monitor(resource: dict) -> dict:
    """Build Prometheus discovery for an operator-managed backend Service."""
    metadata = resource["metadata"]
    name = metadata["name"]
    return {
        "apiVersion": "monitoring.coreos.com/v1",
        "kind": "ServiceMonitor",
        "metadata": {
            "name": name,
            "namespace": metadata["namespace"],
            "labels": {**_labels(name), "release": "observability"},
            "ownerReferences": _owner_reference(resource),
        },
        "spec": {
            "selector": {
                "matchLabels": {"app.kubernetes.io/name": name},
            },
            "endpoints": [
                {"port": "http", "path": "/metrics", "interval": "15s"}
            ],
        },
    }


def build_canary_prometheus_rule(resource: dict) -> dict | None:
    """Build the optional canary error-rate alert managed by Prometheus."""
    metadata = resource["metadata"]
    canary = resource["spec"].get("canary")
    if not canary:
        return None
    analysis = canary.get("analysis", {})
    if analysis.get("enabled", True) is False:
        return None

    name = metadata["name"]
    namespace = metadata["namespace"]
    window_minutes = analysis.get("windowMinutes", 5)
    threshold = analysis.get("maxErrorRatePercent", 5)
    duration_minutes = analysis.get("forMinutes", 2)
    selector = (
        f'namespace={json.dumps(namespace)},track="canary"'
    )
    error_selector = f'{selector},status="error"'
    expression = (
        "100 * "
        f"sum(rate(kubelaunch_prompt_requests_total{{{error_selector}}}"
        f"[{window_minutes}m])) / "
        "clamp_min("
        f"sum(rate(kubelaunch_prompt_requests_total{{{selector}}}"
        f"[{window_minutes}m])), 0.001) > {threshold}"
    )
    return {
        "apiVersion": "monitoring.coreos.com/v1",
        "kind": "PrometheusRule",
        "metadata": {
            "name": f"{name}-canary",
            "namespace": namespace,
            "labels": {**_labels(name), "release": "observability"},
            "ownerReferences": _owner_reference(resource),
        },
        "spec": {
            "groups": [
                {
                    "name": f"{name}.canary",
                    "rules": [
                        {
                            "alert": "KubeLaunchCanaryHighErrorRate",
                            "expr": expression,
                            "for": f"{duration_minutes}m",
                            "labels": {
                                "severity": "warning",
                                "aiworkload": name,
                            },
                            "annotations": {
                                "summary": (
                                    f"Canary error rate is above {threshold}% "
                                    f"for AIWorkload {namespace}/{name}"
                                )
                            },
                        }
                    ],
                }
            ]
        },
    }
