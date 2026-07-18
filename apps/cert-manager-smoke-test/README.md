# cert-manager smoke test

Denne appen brukes bare av `--full`-profilen. En selvsignert `ClusterIssuer`
utsteder et kortlivet sertifikat for `kubelaunch.local`. Når sertifikatet er
klart, finnes TLS-materialet i Secret `kubelaunch-selfsigned-tls` i namespace
`kubelaunch-system`.

Kontroller testen med:

```console
kubectl --context k3d-kubelaunch --namespace kubelaunch-system get certificate,secret
```
