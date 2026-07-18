# Plattform

Denne mappen er inngangen til GitOps-oppsettet. CLI-et legger inn
`root-application.yaml`, og Argo CD synkroniserer resten av plattformen herfra.
CLI-et skal ikke installere komponentene én etter én.

Root Application leser YAML-filer rekursivt. Child Applications ligger i
`components/` og peker videre på Kustomize-oppsett under `apps/`.

Dette er minimalprofilens root. Fullprofilen ligger under `profiles/full/` og
kombinerer disse child Applications med profilspesifikke komponenter.
