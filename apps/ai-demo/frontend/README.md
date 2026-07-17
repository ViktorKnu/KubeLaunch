# Frontend

Frontenden er en liten statisk webapplikasjon uten byggeverktøy eller eksterne
JavaScript-avhengigheter. Nginx serverer filene og videresender `/api/` til
`ai-demo-backend` i samme Kubernetes-namespace.

Bygg og importer imaget til det lokale k3d-clusteret:

```console
make frontend-image
```

Når Argo CD-applikasjonen er synkronisert, åpnes lokal tilgang med:

```console
make frontend
```

Gå deretter til `http://localhost:8080`.
