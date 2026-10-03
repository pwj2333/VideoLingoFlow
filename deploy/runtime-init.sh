#!/bin/sh
set -eu

config_root=/app/backend/config
data_root=/app/data/config
mkdir -p "$data_root"

# ponytail: only user-editable assets are linked; bundled Python code stays in the image.
for name in asr_interfaces.json imagegen_interfaces.json musicgen_interfaces.json ocr_interfaces.json separation_interfaces.json tts_interfaces.json tts_voices.json videogen_interfaces.json voiceforge.yaml deleted_builtin_node_ids.json subtitle_presets node_types drama_prompts; do
  source="$config_root/$name"
  target="$data_root/$name"
  if [ ! -e "$target" ] && [ -e "$source" ]; then
    cp -a "$source" "$target"
  fi
  if [ -e "$target" ]; then
    rm -rf "$source"
    ln -s "$target" "$source"
  fi
done

for mapping in config.yaml:config.yaml workflows:workflows workflow_groups.json:workflow_groups.json; do
  name=${mapping%%:*}
  target=/app/data/${mapping#*:}
  source="$config_root/$name"
  if [ ! -e "$target" ] && [ -e "$source" ]; then
    cp -a "$source" "$target"
  fi
  if [ -e "$target" ]; then
    rm -rf "$source"
    ln -s "$target" "$source"
  fi
done

for item in /app/config/prompt_templates.json /app/config/voiceforge_prompt_defaults.json /app/config/prompts /app/thirdparty/QM-LocalRouter/backend/data /app/thirdparty/social-auto-upload-web-ui/data /app/control_plane_workspaces /app/tasks /app/output /app/share /app/logs /app/backend/backups; do
  target="/app/data/persisted${item}"
  mkdir -p "$(dirname "$target")"
  if [ ! -e "$target" ]; then
    if [ -e "$item" ] && [ ! -L "$item" ]; then
      cp -a "$item" "$target"
    elif [ "$item" = /app/config/prompt_templates.json ]; then
      continue
    else
      mkdir -p "$target"
    fi
  fi
  rm -rf "$item"
  ln -s "$target" "$item"
done
