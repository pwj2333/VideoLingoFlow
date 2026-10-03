#!/bin/sh
set -eu

image=${1:?Usage: check_runtime_persistence.sh IMAGE}
volume="yunzhiai-persistence-check-$$"
docker volume create "$volume" >/dev/null
trap 'docker volume rm "$volume" >/dev/null' EXIT

docker run --rm -v "$volume:/app/data" "$image" sh -c '
  python /app/runtime-init.py
  test -L /app/backend/config/imagegen_interfaces.json
  test -L /app/control_plane_workspaces
  test -L /app/backend/config/workflows
  printf "\n# persistence-check\n" >> /app/backend/config/voiceforge.yaml
'
docker run --rm -v "$volume:/app/data" "$image" sh -c '
  python /app/runtime-init.py
  grep -q persistence-check /app/backend/config/voiceforge.yaml
  test -L /app/thirdparty/QM-LocalRouter/backend/data
  test -L /app/config/prompt_templates.json
'
echo 'runtime persistence check passed'
