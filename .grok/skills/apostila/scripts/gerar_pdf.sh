#!/usr/bin/env bash
# Converte a apostila HTML em PDF usando o Chrome headless já presente na máquina.
#
# Uso: gerar_pdf.sh <arquivo.html> [saida.pdf]

set -euo pipefail

entrada="${1:?uso: gerar_pdf.sh <arquivo.html> [saida.pdf]}"
[[ -f "$entrada" ]] || { echo "ERRO: arquivo não encontrado: $entrada" >&2; exit 1; }

entrada_abs="$(readlink -f "$entrada")"
saida="${2:-${entrada_abs%.html}.pdf}"

encontrar_chrome() {
  local c
  for c in "$CHROME_BIN" \
           /usr/bin/google-chrome-stable /usr/bin/google-chrome \
           /usr/bin/chromium /usr/bin/chromium-browser \
           /opt/google/chrome/chrome; do
    [[ -n "${c:-}" && -x "$c" ]] && { echo "$c"; return 0; }
  done
  # Navegadores baixados pelo Playwright — o mais recente primeiro.
  for c in $(ls -d "$HOME"/.cache/ms-playwright/chromium-*/chrome-linux*/chrome 2>/dev/null | sort -V -r); do
    [[ -x "$c" ]] && { echo "$c"; return 0; }
  done
  return 1
}

CHROME_BIN="${CHROME_BIN:-}"
chrome="$(encontrar_chrome)" || {
  cat >&2 <<'MSG'
ERRO: nenhum Chrome/Chromium encontrado.
Defina CHROME_BIN=/caminho/do/chrome, ou instale um navegador, ou abra o HTML
no seu navegador e imprima com Ctrl+P > Salvar como PDF (mesmo resultado).
MSG
  exit 1
}

perfil="$(mktemp -d)"
trap 'rm -rf "$perfil"' EXIT

"$chrome" \
  --headless \
  --disable-gpu \
  --no-sandbox \
  --no-pdf-header-footer \
  --user-data-dir="$perfil" \
  --virtual-time-budget=10000 \
  --print-to-pdf="$saida" \
  "file://$entrada_abs" 2>/dev/null

[[ -s "$saida" ]] || { echo "ERRO: o Chrome não produziu o PDF" >&2; exit 1; }

paginas="$(pdfinfo "$saida" 2>/dev/null | awk '/^Pages:/{print $2}')"
echo "pdf: $saida${paginas:+ (${paginas} páginas)}"
