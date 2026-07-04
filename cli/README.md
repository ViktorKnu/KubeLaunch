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

Kommandoene sjekker foreløpig at `kubectl`, `k3d` og `helm` finnes i `PATH`.
Opprettelse og sletting av cluster kommer i milepæl 2.

```console
kube-launch up --minimal
kube-launch status
kube-launch down
```

Tester og lint kjøres slik:

```console
python -m pytest
python -m ruff check .
```
