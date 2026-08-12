# Eksisterende sky-cluster

KubeLaunch kan bootstrappe GitOps-plattformen i et eksisterende Kubernetes-
cluster. Kommandoen oppretter ikke AKS, EKS eller GKE og endrer aldri hvilket
kube-context som er aktivt. Context må oppgis eksplisitt på hver kjøring.

## Før du starter

Du trenger:

- et eksisterende cluster og et fungerende kube-context
- `kubectl` og `helm`
- en Git-fork som Argo CD kan lese
- pullbare backend- og frontend-images i et container-register
- et pullbart operator-image dersom fullprofilen brukes

Bruk immutable image-tagger, gjerne Git-SHA, i stedet for `latest`. For et privat
Git-repo eller container-register må nødvendige Argo CD- og imagePullSecrets
konfigureres separat.

## Bygg og publiser images

Erstatt register, repository og tag med dine egne verdier:

```console
docker build -t registry.example/kubelaunch-backend:git-sha apps/ai-demo/backend
docker build -t registry.example/kubelaunch-frontend:git-sha apps/ai-demo/frontend
docker build -t registry.example/kubelaunch-operator:git-sha apps/aiworkload-operator
docker push registry.example/kubelaunch-backend:git-sha
docker push registry.example/kubelaunch-frontend:git-sha
docker push registry.example/kubelaunch-operator:git-sha
```

## Bootstrap

Minimalprofilen er anbefalt som første kontroll:

```powershell
python -m kube_launch bootstrap `
  --context mitt-sky-context `
  --profile minimal `
  --repo-url https://github.com/example/KubeLaunch.git `
  --revision git-sha `
  --backend-image registry.example/kubelaunch-backend:git-sha `
  --frontend-image registry.example/kubelaunch-frontend:git-sha
```

CLI-et kontrollerer context, ber om bekreftelse, installerer den pinnede Argo CD-
versjonen og legger inn én root Application. Repo, revision og image-overrides
propageres videre til Git-baserte child Applications. Helm-baserte komponenter
beholder sine pinnede chart-kilder.

Fullprofilen krever i tillegg `--operator-image`. Den inkluderer en usikker,
flyktig Vault dev-instans og selvsignert TLS og er derfor bare en demonstrasjon,
ikke et produksjonsoppsett.

## Verifisering

```console
kubectl --context mitt-sky-context --namespace argocd get applications
kubectl --context mitt-sky-context --namespace ai-demo get deployment,service,pods
kubectl --context mitt-sky-context --namespace monitoring get pods
```

KubeLaunch oppretter foreløpig ikke Ingress, offentlig DNS eller LoadBalancer.
Tilgang skjer derfor med port-forward eller med et eget ingress-oppsett i
forken. Lagringsklasse, ressursgrenser, GPU-noder, TLS-issuer og secret backend
bør også tilpasses den valgte skyleverandøren.

## Valgfri HTTPS-ingress

Bootstrap kan opprette en leverandørnøytral `Ingress` og et cert-manager
`Certificate` for frontenden. Clusteret må allerede ha:

- en ingress-controller og tilhørende `IngressClass`
- cert-manager og en fungerende `ClusterIssuer`
- DNS som peker hostname til ingress-controllerens offentlige adresse

KubeLaunch installerer ingen ingress-controller og oppretter ikke offentlig DNS
eller en produksjons-issuer. Aktiver overlayet ved å legge til:

```powershell
  --ingress-hostname ai.example.com `
  --ingress-class min-ingress-class `
  --cluster-issuer letsencrypt-production
```

Alle tre argumentene kreves sammen. Overlayet oppretter TLS-secret
`kubelaunch-frontend-tls` i `ai-demo` og sender `/` til frontend-servicen.

`kube-launch down` gjelder bare det lokale k3d-clusteret og skal ikke brukes som
oppryddingskommando for et sky-cluster. Endringer og rollback bør gjøres i Git;
alternativt kan bootstrap kjøres på nytt med en tidligere immutable revision.
