# Plattform

Denne mappen er inngangen til GitOps-oppsettet. CLI-et legger inn
`root-application.yaml`, og Argo CD synkroniserer resten av plattformen herfra.
CLI-et skal ikke installere komponentene én etter én.

Root Application renderer Kustomize-oppsettet i `components/`. Child
Applications peker videre på Kustomize-oppsett under `apps/`. Git-baserte child
Applications har labelen `kubelaunch.dev/source=git`, slik at bootstrap av et
eksisterende cluster kan propagere fork og revision uten å endre Helm-kildene.

Dette er minimalprofilens root. Fullprofilen ligger under `profiles/full/` og
kombinerer disse child Applications med profilspesifikke komponenter.
