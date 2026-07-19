# Full profil

Fullprofilen gjenbruker alle Applications under `platform/components/` og legger
til komponentene i `components/`. CLI-et aktiverer profilen med
`kube-launch up --full`.

Den første utvidelsen er cert-manager med CRD-er administrert av Helm og en
selvsignert sertifikattest. Bytt tilbake til minimalprofilen med
`kube-launch up --minimal`; Argo CD fjerner da fullprofilens child Applications.

Fullprofilen inkluderer også External Secrets Operator og en lokal Vault i
dev-modus. En bootstrap-jobb skriver en testverdi til Vault, og en
`ExternalSecret` synkroniserer verdien til et Kubernetes Secret. Vault-data og
den kjente demo-tokenen er flyktige og må aldri brukes i produksjon.
