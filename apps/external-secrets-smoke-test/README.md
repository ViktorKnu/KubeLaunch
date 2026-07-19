# External Secrets smoke test

En namespaced `SecretStore` kobler External Secrets Operator til den lokale
Vault-instansen. `ExternalSecret` leser `secret/kubelaunch/demo` og oppretter
Kubernetes Secret `kubelaunch-vault-demo` i `kubelaunch-system`.

Kontroller flyten med:

```console
kubectl --context k3d-kubelaunch --namespace kubelaunch-system get secretstore,externalsecret,secret
```

Vault kjører i dev-modus; integrasjonen er kun for lokal demonstrasjon.
