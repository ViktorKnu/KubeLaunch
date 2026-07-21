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
kube-launch up --full
kube-launch status
kube-launch down
```

`up --minimal` og `up --full` er idempotente og lar et eksisterende cluster være
i fred. Minimalprofilen installerer MVP-plattformen. Fullprofilen bruker de samme
komponentene og legger i tillegg til cert-manager med en selvsignert
sertifikattest, External Secrets Operator, en lokal Vault-demo og
`AIWorkload`-operatoren. Profilen kan byttes ved å kjøre den andre
`up`-kommandoen; Argo CD synkroniserer og rydder komponentforskjellene.
`status` sjekker om clusteret finnes, om Kubernetes API-et svarer og om alle
forventede Argo CD-applikasjoner er `Synced` og `Healthy`.
`down` ber om bekreftelse; bruk `down --yes` i automatiserte kjøringer.

Nye cluster eksponerer Kubernetes API-et på `127.0.0.1` for å unngå lokale
DNS-problemer med `host.docker.internal`. Etter opprettelse venter CLI-et i
opptil to minutter og prøver readiness-endepunktet flere ganger.

Når clusteret er klart, installerer `up` Argo CD med Helm og venter til
installasjonen er klar. Til slutt legges `platform/root-application.yaml` inn i
clusteret. Root Application peker på `platform/` i dette repoet; alle andre
komponenter skal etter hvert synkroniseres av Argo CD.

`status` viser samlet sync og health for smoke-testene, observability, KEDA,
Ollama, backend og frontend. Kommandoen viser også port-forward-kommandoer for
frontenden, Grafana og Ollama. Den returnerer feilkode hvis en obligatorisk
komponent mangler eller ikke er klar. For fullprofilen vises også cert-manager
sertifikattesten, Vault, External Secrets-flyten og operatoren automatisk.

Tester og lint kjøres slik:

```console
python -m pytest
python -m ruff check .
```
