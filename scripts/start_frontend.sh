#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../frontend"
if [ ! -d node_modules ]; then
  npm ci
fi
npm run dev
