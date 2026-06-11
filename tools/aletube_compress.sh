#!/usr/bin/env bash
# aletube_compress.sh — comprime vídeo para upload no AleTubeGames.
#
# Resultado: ficheiro mp4 com qualidade boa, tipicamente <80MB para 1080p
# de até ~5min, dentro do limite do ingress do HF Space free (100MB).
#
# Uso:
#   ./tools/aletube_compress.sh INPUT.mp4 [OUTPUT.mp4]
#
# Requer: ffmpeg

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 INPUT.mp4 [OUTPUT.mp4]" >&2
  exit 1
fi

INPUT="$1"
OUTPUT="${2:-${INPUT%.*}_compressed.mp4}"

if [[ ! -f "$INPUT" ]]; then
  echo "Erro: ficheiro não encontrado: $INPUT" >&2
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Erro: ffmpeg não está instalado. Instala: sudo apt install ffmpeg" >&2
  exit 1
fi

SIZE_BEFORE=$(stat -c%s "$INPUT")
SIZE_BEFORE_MB=$(( SIZE_BEFORE / 1024 / 1024 ))
echo "→ Input:  $INPUT (${SIZE_BEFORE_MB} MB)"
echo "→ Output: $OUTPUT"
echo "→ A comprimir... (pode demorar alguns minutos)"
echo ""
echo "⚠ ATENÇÃO: Se este vídeo for subir para o YouTube, NÃO use este script."
echo "  O YouTube re-encodeia o vídeo, e a compressão dupla (CRF + YouTube)"
echo "  degrada a qualidade visivelmente. Suba o arquivo ORIGINAL diretamente"
echo "  com o aletube_youtube_upload.py."
echo ""

# H.264 CRF 26 = qualidade boa, ~30-40% do tamanho original em vídeos típicos.
# preset medium = equilíbrio entre velocidade e compressão.
# -movflags +faststart = mp4 web-friendly (metadata no início).
# Audio AAC 128k é suficiente para vídeo de jogos.
ffmpeg -y -i "$INPUT" \
  -c:v libx264 -preset medium -crf 26 \
  -c:a aac -b:a 128k \
  -movflags +faststart \
  -loglevel warning -stats \
  "$OUTPUT"

SIZE_AFTER=$(stat -c%s "$OUTPUT")
SIZE_AFTER_MB=$(( SIZE_AFTER / 1024 / 1024 ))
RATIO=$(( SIZE_AFTER * 100 / SIZE_BEFORE ))

echo ""
echo "✓ Concluído"
echo "  Antes:  ${SIZE_BEFORE_MB} MB"
echo "  Depois: ${SIZE_AFTER_MB} MB (${RATIO}% do original)"

if [[ $SIZE_AFTER_MB -gt 95 ]]; then
  echo ""
  echo "⚠ Ainda > 95 MB. Se o upload no HF falhar, repete com CRF mais alto:"
  echo "  ffmpeg -y -i \"$INPUT\" -c:v libx264 -preset medium -crf 30 -c:a aac -b:a 96k -movflags +faststart \"$OUTPUT\""
fi
