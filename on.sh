#!/bin/sh
set -e
umask 077
cd -- "$(dirname -- "$0")"

# Mesma sequência enxuta do LIRA; o Compose resolve os IDs do .env.
CCAA_IDS=$(docker compose -f docker-compose.yml config --format json |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["services"]["ccaa"]["user"])')

mkdir -p databases runtime

docker compose -f docker-compose.yml stop ccaa

sudo python3 testes/hosted.py --init-auth runtime
sudo chown -R -- "$CCAA_IDS" databases runtime
sudo chmod -R u+rwX databases runtime
sudo chmod 700 databases runtime

docker build -t ccaa:local .

docker compose -f docker-compose.yml up -d \
  --no-build \
  --pull never \
  --force-recreate ccaa

docker compose -f docker-compose.yml logs --tail=50 ccaa
printf '\nLogin local: sudo less runtime/acesso.txt (não publique esse arquivo).\n'
