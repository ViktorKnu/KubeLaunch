# KEDA smoke test

Denne appen tester KEDA uten å blande inn AI-demoen. Workloaden er Kubernetes
sitt enkle `hpa-example`, og et `ScaledObject` holder mellom én og tre replikaer
basert på CPU-bruk.

CPU-scaleren trenger Metrics Server og en CPU request på containeren. Begge
deler er dekket her: k3s leverer Metrics Server som standard, og Deployment har
en request på `200m`.

Se [hoved-README-en](../../README.md#test-keda-skalering) for lasttesten.
