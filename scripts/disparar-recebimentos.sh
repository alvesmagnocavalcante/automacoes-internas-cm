#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_ACTIONS_TOKEN:?Configure GITHUB_ACTIONS_TOKEN no Semaphore}"

curl --fail --silent --show-error --location \
  --connect-timeout 10 --max-time 30 \
  --request POST \
  --header "Accept: application/vnd.github+json" \
  --header "Authorization: Bearer ${GITHUB_ACTIONS_TOKEN}" \
  --header "Content-Type: application/json" \
  "https://api.github.com/repos/alvesmagnocavalcante/automacoes-internas-cm/actions/workflows/conferencia-recebimentos.yml/dispatches" \
  --data '{"ref":"main"}'

echo "Disparo solicitado ao GitHub Actions."
