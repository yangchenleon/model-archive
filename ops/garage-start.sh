#!/bin/sh
# Start Garage and make the bucket usable, idempotently.
#
# The init runs in the same container as the daemon (not a separate one-shot
# service) so the CLI talks to 127.0.0.1 and no inter-container RPC/DNS is
# involved. Every step guards on current state, so restarting the container on an
# existing volume is a no-op instead of an error.
set -eu

CONFIG=/etc/garage.toml
GARAGE="/garage -c $CONFIG"
BUCKET="${S3_BUCKET:-model-archive-photos}"
KEY="${S3_ACCESS_KEY:?S3_ACCESS_KEY must be set (GK + 24 hex)}"
SECRET="${S3_SECRET_KEY:?S3_SECRET_KEY must be set (64 hex)}"

/garage -c "$CONFIG" server &
SERVER_PID=$!

# Kill the daemon if the container stops; otherwise it is orphaned.
trap 'kill -TERM "$SERVER_PID" 2>/dev/null || true' INT TERM

echo "[garage] waiting for the daemon..."
for _ in $(seq 1 60); do
    if $GARAGE status >/dev/null 2>&1; then break; fi
    sleep 1
done

# Single-node layout: assign the only node, then commit it once.
if $GARAGE status 2>/dev/null | grep -q "NO ROLE ASSIGNED"; then
    NODE_ID=$($GARAGE status 2>/dev/null | awk '/HEALTHY NODES/{getline; getline; print $1; exit}')
    echo "[garage] assigning layout to $NODE_ID"
    $GARAGE layout assign -z dc1 -c 1T "$NODE_ID" >/dev/null
    $GARAGE layout apply --version 1 >/dev/null
fi

if ! $GARAGE key info "$KEY" >/dev/null 2>&1; then
    echo "[garage] importing access key"
    $GARAGE key import --yes -n app "$KEY" "$SECRET" >/dev/null
fi
# The API creates its own bucket on first use; that needs this permission.
$GARAGE key allow --create-bucket "$KEY" >/dev/null 2>&1 || true

if ! $GARAGE bucket info "$BUCKET" >/dev/null 2>&1; then
    echo "[garage] creating bucket $BUCKET"
    $GARAGE bucket create "$BUCKET" >/dev/null
fi
$GARAGE bucket allow --read --write --owner --key "$KEY" "$BUCKET" >/dev/null

echo "[garage] ready: bucket=$BUCKET key=$KEY"
wait "$SERVER_PID"
