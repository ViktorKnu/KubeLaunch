# CLI

The Python/Typer `kube-launch` CLI owns local cluster lifecycle, Argo CD
bootstrap, and platform status reporting. It does not install individual
platform components.

## Local development

From the repository root:

```console
python -m pip install -e ".[dev]"
kube-launch --help
```

The Milestone 1 commands validate that `kubectl`, `k3d`, and `helm` are present
on `PATH`. They do not create, inspect, or delete a cluster yet.

```console
kube-launch up --minimal
kube-launch status
kube-launch down
```

Run the checks with:

```console
python -m pytest
python -m ruff check .
```
