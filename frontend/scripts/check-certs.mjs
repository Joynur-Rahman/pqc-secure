#!/usr/bin/env node
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { execSync } from 'child_process'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..')
const certsDir = path.join(projectRoot, 'certs')
const keyFile = path.join(certsDir, 'server.key')
const certFile = path.join(certsDir, 'server.crt')

// Check if certificates exist
const keyExists = fs.existsSync(keyFile)
const certExists = fs.existsSync(certFile)

if (!keyExists || !certExists) {
  console.log('⚠️  SSL certificates not found. Generating self-signed certificates...\n')

  // Create certs directory if it doesn't exist
  if (!fs.existsSync(certsDir)) {
    fs.mkdirSync(certsDir, { recursive: true })
  }

  try {
    // Generate private key
    execSync(
      `openssl genrsa -out "${keyFile}" 4096 2>/dev/null`,
      { stdio: 'inherit' }
    )

    // Generate self-signed certificate
    execSync(
      `openssl req -new -x509 -key "${keyFile}" -out "${certFile}" -days 365 -subj "/C=US/ST=Development/L=Local/O=PQC-Secure/CN=localhost" 2>/dev/null`,
      { stdio: 'inherit' }
    )

    console.log('✓ Self-signed certificates generated successfully\n')
    console.log('Certificates created at:')
    console.log(`  - ${keyFile}`)
    console.log(`  - ${certFile}\n`)
  } catch (error) {
    console.error('✗ Failed to generate certificates. Make sure OpenSSL is installed.')
    console.error('On macOS: brew install openssl')
    console.error('On Ubuntu/Debian: sudo apt-get install openssl')
    console.error('On Windows: Use Git Bash or WSL\n')
    process.exit(1)
  }
} else {
  console.log('✓ SSL certificates found\n')
}
