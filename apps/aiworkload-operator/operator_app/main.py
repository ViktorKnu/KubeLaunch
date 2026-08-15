"""Watch AIWorkload resources and reconcile backend Deployments and Services."""

import logging
import time

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from operator_app.workload import (
    build_canary_deployment,
    build_deployment,
    build_service,
    build_status_patch,
    rollout_ready_replicas,
)

GROUP = "platform.kubelaunch.dev"
VERSION = "v1alpha1"
PLURAL = "aiworkloads"
LOGGER = logging.getLogger(__name__)
POLL_INTERVAL_SECONDS = 15


def _upsert_deployment(api: client.AppsV1Api, desired: dict) -> None:
    namespace = desired["metadata"]["namespace"]
    name = desired["metadata"]["name"]
    try:
        api.read_namespaced_deployment(name=name, namespace=namespace)
    except ApiException as error:
        if error.status != 404:
            raise
        api.create_namespaced_deployment(namespace=namespace, body=desired)
    else:
        api.patch_namespaced_deployment(name=name, namespace=namespace, body=desired)


def _upsert_service(api: client.CoreV1Api, desired: dict) -> None:
    namespace = desired["metadata"]["namespace"]
    name = desired["metadata"]["name"]
    try:
        api.read_namespaced_service(name=name, namespace=namespace)
    except ApiException as error:
        if error.status != 404:
            raise
        api.create_namespaced_service(namespace=namespace, body=desired)
    else:
        desired["spec"].pop("clusterIP", None)
        api.patch_namespaced_service(name=name, namespace=namespace, body=desired)


def _delete_deployment(api: client.AppsV1Api, *, name: str, namespace: str) -> None:
    try:
        api.delete_namespaced_deployment(name=name, namespace=namespace)
    except ApiException as error:
        if error.status != 404:
            raise


def _ready_replicas(api: client.AppsV1Api, *, name: str, namespace: str) -> int:
    deployment = api.read_namespaced_deployment(name=name, namespace=namespace)
    generation = int(deployment.metadata.generation or 0)
    observed_generation = int(deployment.status.observed_generation or 0)
    ready_replicas = int(deployment.status.ready_replicas or 0)
    updated_replicas = int(deployment.status.updated_replicas or 0)
    return rollout_ready_replicas(
        generation=generation,
        observed_generation=observed_generation,
        ready_replicas=ready_replicas,
        updated_replicas=updated_replicas,
    )


def reconcile(
    resource: dict,
    apps_api: client.AppsV1Api,
    core_api: client.CoreV1Api,
    custom_api: client.CustomObjectsApi,
) -> None:
    """Reconcile one AIWorkload and update its observed status."""
    metadata = resource["metadata"]
    namespace = metadata["namespace"]
    name = metadata["name"]

    _upsert_deployment(apps_api, build_deployment(resource))
    stable_ready_replicas = _ready_replicas(
        apps_api,
        name=name,
        namespace=namespace,
    )
    canary_deployment = build_canary_deployment(resource)
    canary_ready_replicas = 0
    if canary_deployment:
        _upsert_deployment(apps_api, canary_deployment)
        canary_ready_replicas = _ready_replicas(
            apps_api,
            name=f"{name}-canary",
            namespace=namespace,
        )
    else:
        _delete_deployment(
            apps_api,
            name=f"{name}-canary",
            namespace=namespace,
        )
    _upsert_service(core_api, build_service(resource))
    status_patch = build_status_patch(
        resource,
        stable_ready_replicas,
        canary_ready_replicas,
    )
    if status_patch is not None:
        custom_api.patch_namespaced_custom_object_status(
            group=GROUP,
            version=VERSION,
            namespace=namespace,
            plural=PLURAL,
            name=name,
            body={"status": status_patch},
        )
    LOGGER.info("Reconciled AIWorkload %s/%s", namespace, name)


def run() -> None:
    """Run the resilient cluster-wide AIWorkload analysis loop."""
    logging.basicConfig(level=logging.INFO)
    config.load_incluster_config()
    apps_api = client.AppsV1Api()
    core_api = client.CoreV1Api()
    custom_api = client.CustomObjectsApi()

    while True:
        try:
            response = custom_api.list_cluster_custom_object(
                group=GROUP,
                version=VERSION,
                plural=PLURAL,
            )
        except Exception:
            LOGGER.exception("Could not list AIWorkloads; retrying")
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        for resource in response.get("items", []):
            try:
                reconcile(resource, apps_api, core_api, custom_api)
            except Exception:
                metadata = resource.get("metadata", {})
                LOGGER.exception(
                    "Could not reconcile AIWorkload %s/%s",
                    metadata.get("namespace", "unknown"),
                    metadata.get("name", "unknown"),
                )
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
