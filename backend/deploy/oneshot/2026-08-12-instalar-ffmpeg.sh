#!/usr/bin/env bash
# O passo zero do vídeo (video_flow.py) extrai quadros com ffmpeg.
# Sem ele o handler responde "extrator não instalado" — este oneshot fecha
# isso no primeiro deploy. Idempotente: apt não reinstala o que já está lá.
set -euo pipefail
if command -v ffmpeg >/dev/null 2>&1; then
    echo "ffmpeg já instalado: $(ffmpeg -version | head -1)"
    exit 0
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ffmpeg
echo "ffmpeg instalado: $(ffmpeg -version | head -1)"
