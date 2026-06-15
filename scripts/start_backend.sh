#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../backend"
python manage.py runserver 127.0.0.1:8000
