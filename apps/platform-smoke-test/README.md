# Smoke test

Dette er en liten nginx-app som bekrefter at GitOps-flyten virker. Root
Application oppretter child Application, og child Application synkroniserer
disse Kustomize-filene til namespace `kubelaunch-system`.

Appen er bare en midlertidig plattformtest. Den kan fjernes når de faktiske
komponentene har overtatt som bekreftelse på at Argo CD fungerer.

Render manifestene lokalt med:

```console
kubectl kustomize apps/platform-smoke-test
```
