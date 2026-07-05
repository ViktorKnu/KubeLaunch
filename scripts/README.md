# Hjelpescript

Små script for lokal testing kan legges her når vi faktisk trenger dem. Selve
installasjonen av plattformen skal ligge i GitOps-oppsettet, ikke i ett stort
script som gjør alt.

`validate_manifests.py` leser alle YAML-filer under `platform/` og `apps/` og
sjekker at de har grunnfeltene Kubernetes forventer.
