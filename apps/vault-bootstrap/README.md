# Vault bootstrap

Denne appen brukes bare av fullprofilens lokale demo. Vault kjører i dev-modus,
og den kjente tokenen `kubelaunch-dev-only` ligger derfor med vilje i Git.
PostSync-jobben venter på Vault og skriver én testverdi til KV v2-stien
`secret/kubelaunch/demo`.

Dette oppsettet er usikkert, flyktig og må aldri brukes i produksjon.
