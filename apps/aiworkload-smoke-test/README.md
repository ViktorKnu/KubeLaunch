# AIWorkload smoke test

Fullprofilen oppretter `AIWorkload/operator-demo` i namespace `ai-workloads`.
Operatoren skal opprette Deployment og Service med samme navn og rapportere
fasen `Reconciled` i CR-status.

```console
make aiworkload-status
```
