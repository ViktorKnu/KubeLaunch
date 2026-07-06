# Ollama

Ollama kjører som én CPU-basert runtime bak en intern Service. Modellfilene
ligger på PVC-en `ollama-models`, slik at `tinyllama` ikke må lastes ned på nytt
hver gang podden starter.

En Argo CD PostSync-jobb kjører `ollama pull tinyllama` etter at Deployment er
klar. Pull-operasjonen er idempotent og jobben fjernes etter en vellykket sync.

Se [hoved-README-en](../../README.md#test-ollama-direkte) for port-forward og
curl-eksempel.
