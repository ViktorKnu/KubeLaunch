# AIWorkload operator

Operatoren watcher namespaced `AIWorkload`-ressurser og reconcilerer hver av dem
til en FastAPI-backend Deployment og Service. Feltet `spec.model` velger
Ollama-modell, mens `spec.runtimeURL`, `spec.image` og `spec.replicas` kan
overstyres.

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
