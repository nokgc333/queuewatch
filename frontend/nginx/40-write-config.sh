#!/bin/sh
# コンテナ起動時に、環境変数から /config.js を書く(同じイメージを、環境ごとに作り直さずに使うため)。
set -eu

escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

cat > /tmp/config.js <<CONFIG
window.__QUEUEWATCH_CONFIG__ = {
  apiBaseUrl: "$(escape "${API_ORIGIN:-}")",
  apiToken: "$(escape "${API_TOKEN:-}")"
};
CONFIG
