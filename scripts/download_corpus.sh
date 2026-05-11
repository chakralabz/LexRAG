#!/usr/bin/env bash
set -euo pipefail

RAW_DIR="data/raw"
LOG_FILE="${RAW_DIR}/download.log"
FAILED=0
DOWNLOADED=0
BYTES=0

mkdir -p "${RAW_DIR}/sec" "${RAW_DIR}/court" "${RAW_DIR}/regulation"
: > "${LOG_FILE}"

log() {
  printf '%s\n' "$1" | tee -a "${LOG_FILE}"
}

safe_download() {
  local url="$1"
  local out="$2"

  if curl -fL --max-time 120 --retry 2 --retry-delay 2 -o "${out}" "${url}"; then
    local size
    size=$(wc -c < "${out}" | tr -d ' ')
    DOWNLOADED=$((DOWNLOADED + 1))
    BYTES=$((BYTES + size))
    log "OK  ${out} (${size} bytes)"
  else
    FAILED=$((FAILED + 1))
    log "ERR ${out} from ${url}"
  fi
}

log "Starting corpus download..."

# SEC EDGAR companyfacts endpoint samples (placeholder CIK list for bootstrap).
SEC_CIKS=(
  0000320193
  0000789019
  0001652044
  0001018724
  0001326801
)
for cik in "${SEC_CIKS[@]}"; do
  safe_download \
    "https://data.sec.gov/api/xbrl/companyfacts/CIK${cik}.json" \
    "${RAW_DIR}/sec/companyfacts_${cik}.json"
done

# EU AI Act from EUR-Lex public PDF.
safe_download \
  "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202401689" \
  "${RAW_DIR}/regulation/eu_ai_act.pdf"

# CourtListener sample opinions API pages (public).
for page in $(seq 1 20); do
  safe_download \
    "https://www.courtlistener.com/api/rest/v4/opinions/?page=${page}" \
    "${RAW_DIR}/court/opinions_page_${page}.json"
done

MB=$(awk -v b="${BYTES}" 'BEGIN { printf "%.2f", b / 1024 / 1024 }')
log "Completed. files=${DOWNLOADED} failed=${FAILED} total_mb=${MB}"

if [[ "${FAILED}" -gt 0 ]]; then
  exit 1
fi
