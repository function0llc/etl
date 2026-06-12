#!/bin/zsh
# Seed the cemetery database with sample data

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

python3 "./seed_cemetery_agent.py" \
  --api-url http://localhost:4000 \
  --email admin@cemetery.nul \
  --password admin123 \
  --cemetery-name "Sample_Cemetery" \
  --section-name "North Section" \
  --section-address "250 E Viola St" \
  --section-city "Casa Grande" \
  --section-state "AZ" \
  --section-zip "85122" \
  --interred-first-name "Jane" \
  --interred-last-name "Smith" \
  --is-veteran \
  --plot-status "interred" \
  --payment-status "paid" \
  --date-of-birth "1935-03-15T00:00:00.000Z" \
  --date-of-death "2018-07-22T00:00:00.000Z"
