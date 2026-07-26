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

Eksempelet [examples/vllm.yaml](examples/vllm.yaml) viser kobling mot en vLLM-
server. KubeLaunch installerer ikke vLLM automatisk, siden praktisk lokal
kjøring normalt krever et vesentlig tyngre modell- og maskinvareoppsett enn
Ollama-demoen.
