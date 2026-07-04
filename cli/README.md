# CLI

`kube-launch` er skrevet i Python med Typer. CLI-et skal håndtere livsløpet til
det lokale clusteret, bootstrap av Argo CD og en samlet status for plattformen.
Det skal ikke installere hver enkelt plattformkomponent direkte.

## Lokal utvikling

Kjør dette fra roten av repoet:

```console
python -m pip install -e ".[dev]"
kube-launch --help
```

Kommandoene sjekker at nødvendige verktøy finnes i `PATH`. Clusteret heter
`kubelaunch`, og Kubernetes-konteksten er `k3d-kubelaunch`.

```console
kube-launch up --minimal
kube-launch status
kube-launch down
```

`up --minimal` er idempotent og lar et eksisterende cluster være i fred.
`status` sjekker både om clusteret finnes og om Kubernetes API-et svarer.
`down` ber om bekreftelse; bruk `down --yes` i automatiserte kjøringer.

Tester og lint kjøres slik:

```console
python -m pytest
python -m ruff check .
```
