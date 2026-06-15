#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT="${1:-/tf/ECG-main/LC/medical hack 2025}"
TARGET_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/backend/weights"

mkdir -p "${TARGET_ROOT}/finetune" "${TARGET_ROOT}/pretrain"

cp "${SOURCE_ROOT}/weights_finetune/super_class_stmem.pth" "${TARGET_ROOT}/finetune/"
cp "${SOURCE_ROOT}/weights_finetune/super_class_convnext.pth" "${TARGET_ROOT}/finetune/"
cp "${SOURCE_ROOT}/weights_finetune/super_class_multi.pth" "${TARGET_ROOT}/finetune/"
cp "${SOURCE_ROOT}/weights_pretrain/stmem_encoder.pth" "${TARGET_ROOT}/pretrain/"

echo "CardioSight weights copied into ${TARGET_ROOT}"
