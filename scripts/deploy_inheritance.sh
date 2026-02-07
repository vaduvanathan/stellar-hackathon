#!/usr/bin/env bash
# Deploy the Walletsurance inheritance contract to Soroban Testnet.
# Prereqs: stellar CLI, wasm built, and a funded testnet account (identity configured).
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WASM_DIR="$REPO_ROOT/walletsurance"
WASM_PATH="$WASM_DIR/target/wasm32v1-none/release/inheritance.wasm"

if [[ ! -f "$WASM_PATH" ]]; then
  echo "Building contract..."
  (cd "$WASM_DIR" && stellar contract build)
fi

if [[ ! -f "$WASM_PATH" ]]; then
  echo "ERROR: $WASM_PATH not found after build."
  exit 1
fi

echo "Deploying inheritance contract to Testnet..."
# You must have identity configured: stellar keys add default
# Fund testnet account: https://laboratory.stellar.org/#account-creator?network=test
SOURCE="${STELLAR_SOURCE_ACCOUNT:-default}"
CONTRACT_ID=$(cd "$WASM_DIR" && stellar contract deploy \
  --wasm "$WASM_PATH" \
  --network testnet \
  --source-account "$SOURCE" 2>/dev/null || true)

if [[ -z "$CONTRACT_ID" ]]; then
  echo "Deploy failed or stellar CLI not configured."
  echo "Configure identity: stellar keys add default"
  echo "Fund testnet account: https://laboratory.stellar.org/#account-creator?network=test"
  exit 1
fi

echo "Deployed contract ID: $CONTRACT_ID"
echo "Set in your environment: export CONTRACT_ID=$CONTRACT_ID"
