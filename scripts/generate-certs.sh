#!/bin/bash
# Generate self-signed SSL certificates for local HTTPS development

set -e

# Create certs directory if it doesn't exist
mkdir -p frontend/certs

# Generate private key (4096-bit RSA)
openssl genrsa -out frontend/certs/server.key 4096

# Generate self-signed certificate (valid for 365 days)
openssl req -new -x509 -key frontend/certs/server.key \
  -out frontend/certs/server.crt \
  -days 365 \
  -subj "/C=US/ST=Development/L=Local/O=PQC-Secure/CN=localhost"

echo "✓ Self-signed certificates generated successfully"
echo ""
echo "Certificates created at:"
echo "  - frontend/certs/server.key (private key)"
echo "  - frontend/certs/server.crt (certificate)"
echo ""
echo "These certificates are for local development only."
echo "You may see browser warnings about untrusted certificates - this is expected."
