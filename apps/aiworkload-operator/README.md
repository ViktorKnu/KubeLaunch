# AIWorkload operator

Operatoren watcher namespaced `AIWorkload`-ressurser og reconcilerer hver av dem
til en FastAPI-backend Deployment og Service. Feltet `spec.model` velger
modell, mens `spec.runtime` velger `ollama` eller `vllm`. `spec.runtimeURL`,
`spec.image` og `spec.replicas` kan overstyres. Operatoren velger lokal Ollama-
eller vLLM-service som standard-URL basert på runtime.

Bygg og importer operator-imaget før fullprofilen aktiveres:

```console
make operator-image
```

Eksempel:

```yaml
apiVersion: platform.kubelaunch.dev/v1alpha1
kind: AIWorkload
metadata:
  name: min-modell
spec:
  model: tinyllama
  replicas: 1
```

Genererte ressurser har owner reference til `AIWorkload` og blir derfor ryddet
opp av Kubernetes når CR-en slettes.

## Canary

`spec.canary` oppretter en separat `<navn>-canary` Deployment. Den kan velge en
annen modell, runtime, runtime-URL, image og replica-verdi. Stabil og canary har
ikke-overlappende Deployment-selectors, men deler en egen traffic-group-label
som Service velger. Trafikkandelen er derfor omtrent
`canary replicas / totale replicas`.
Modellen må allerede være tilgjengelig i runtime; operatoren administrerer
backend-utrullingen, men laster ikke modeller automatisk.

Se [examples/canary.yaml](examples/canary.yaml). Promoter en canary ved å kopiere
verdiene til hovedfeltene og fjerne `spec.canary`. Operatoren sletter da canary-
Deploymenten og rydder canary-feltene fra status.

Operatoren analyserer Deployment-readiness hvert 15. sekund. Status er
`CanaryProgressing` frem til både stabil og canary har ønsket antall oppdaterte,
klare replikaer, og endres deretter til `CanaryReady`. Conditions
`StableReady` og `CanaryReady` forklarer hvilken del som eventuelt mangler.
Dette er en rollout-sikkerhetssjekk, ikke automatisk promotering eller analyse
av modellkvalitet.

Når canary finnes, oppretter operatoren også en `ServiceMonitor` og en
`PrometheusRule`. Backenden merker metrics med `model`, `runtime` og `track`, og
regelen varsler når canary-feilraten overstiger terskelen. Standard er mer enn
5 prosent feil over 5 minutter i minst 2 minutter:

```yaml
canary:
  model: qwen2:0.5b
  analysis:
    enabled: true
    maxErrorRatePercent: 5
    windowMinutes: 5
    forMinutes: 2
```

Sett `enabled: false` for å beholde readinessanalysen uten feilratealert.
Alerten blokkerer eller promoterer ikke automatisk; den gir et eksplisitt signal
som må vurderes før canary-verdiene flyttes til hovedfeltene.

Eksempelet [examples/vllm.yaml](examples/vllm.yaml) viser kobling mot en vLLM-
server. KubeLaunch installerer ikke vLLM automatisk, siden praktisk lokal
kjøring normalt krever et vesentlig tyngre modell- og maskinvareoppsett enn
Ollama-demoen.
