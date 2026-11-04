#!/bin/sh
# Sobe como root só pra acertar o dono da pasta de dados (o disco da Railway, um
# volume do Docker ou uma pasta do host chegam montados como root) e logo troca
# pro usuário comum `ceq`. O app em si nunca roda como root.
set -e
DIR="${DATA_DIR:-/data}"
if [ "$(id -u)" = "0" ]; then
  mkdir -p "$DIR"
  chown -R ceq:ceq "$DIR"
  exec setpriv --reuid=ceq --regid=ceq --init-groups "$@"
fi
exec "$@"
