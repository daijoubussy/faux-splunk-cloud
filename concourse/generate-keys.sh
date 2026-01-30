#!/bin/bash
# Generate Concourse SSH keys
# Run this once before starting Concourse

set -e

KEYS_DIR="${1:-./keys}"

echo "=========================================="
echo "Concourse Key Generation"
echo "=========================================="
echo "Keys directory: ${KEYS_DIR}"

mkdir -p "$KEYS_DIR"
cd "$KEYS_DIR"

# Generate TSA host key (for web component)
if [ ! -f tsa_host_key ]; then
    echo "Generating TSA host key..."
    ssh-keygen -t rsa -b 4096 -f tsa_host_key -N ''
else
    echo "TSA host key already exists"
fi

# Generate worker key
if [ ! -f worker_key ]; then
    echo "Generating worker key..."
    ssh-keygen -t rsa -b 4096 -f worker_key -N ''
else
    echo "Worker key already exists"
fi

# Generate session signing key
if [ ! -f session_signing_key ]; then
    echo "Generating session signing key..."
    ssh-keygen -t rsa -b 4096 -f session_signing_key -N ''
else
    echo "Session signing key already exists"
fi

# Copy worker public key to authorized keys
cp worker_key.pub authorized_worker_keys

echo ""
echo "=========================================="
echo "Key Generation Complete!"
echo "=========================================="
echo ""
echo "Generated files:"
ls -la "$KEYS_DIR"
