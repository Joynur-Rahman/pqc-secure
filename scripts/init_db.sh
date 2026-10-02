#!/bin/bash
# Database initialization script
# This script initializes the PQC-Secure database and optionally seeds demo data

set -e

DB_INIT_DEMO=${DB_INIT_DEMO:-false}
DB_VERIFY_HEALTH=${DB_VERIFY_HEALTH:-true}

echo "=========================================="
echo "PQC-Secure Database Initialization"
echo "=========================================="

# Initialize database
echo "Initializing database..."
python -m pqc_secure.db.cli init

# Verify database health
if [ "$DB_VERIFY_HEALTH" = "true" ]; then
    echo ""
    echo "Verifying database health..."
    python -m pqc_secure.db.cli health
fi

# Display status
echo ""
echo "Displaying database status..."
python -m pqc_secure.db.cli status

# Optionally seed demo data
if [ "$DB_INIT_DEMO" = "true" ]; then
    echo ""
    echo "Seeding demo data..."
    python -m pqc_secure.db.cli seed
fi

echo ""
echo "=========================================="
echo "Database initialization completed!"
echo "=========================================="
